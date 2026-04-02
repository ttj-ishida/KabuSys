KEEP A CHANGELOG形式で以下の通り作成しました。バージョンはパッケージ内の __version__ (0.1.0) に合わせた「初回リリース」として記述しています。

CHANGELOG.md
============
全般的な方針: このリリースでは「データ取得・ETL」「研究用ファクター計算」「ニュースNLP／市場レジーム判定」「プロジェクト設定管理（.env）」「マーケットカレンダー管理」の基盤機能を提供します。設計上、DuckDB を用いたローカル分析基盤、OpenAI の JSON Mode を用いた堅牢な LLM 呼び出し、及びルックアヘッドバイアス防止のため日付参照の注意（datetime.today() を直接参照しない）を重視しています。

Unreleased
----------

0.1.0 - 2026-04-02
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開用 __init__.py（__version__ = "0.1.0"）を追加。
  - モジュール公開一覧に data / strategy / execution / monitoring を定義（strategy 等は将来拡張想定）。

- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順序をサポート。OS 環境変数は保護され、.env.local は上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。
  - 複雑な .env 行のパースを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いの差異処理）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB /監視 / システム設定をプロパティ経由で提供。必須環境変数は _require() で明示的にエラーを出す。
  - KABUSYS_ENV や LOG_LEVEL の検証（許容値チェック）を追加。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して、銘柄別にニューステキストを結合し OpenAI（gpt-4o-mini）の JSON Mode で一括評価する処理を実装。
  - バッチ処理: 最大 _BATCH_SIZE=20 銘柄単位で分割し、1銘柄あたり最大の記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行/バックオフ: 429（レート制限）、ネットワーク断、タイムアウト、5xx に対して指数的バックオフでリトライ（最大回数制御）。
  - レスポンス検証ロジックを実装（JSON パースの堅牢化、"results" フィールド検証、未知コードの無視、スコアの数値変換と有限性チェック）。
  - スコアを ±1.0 でクリップして ai_scores テーブルへ idempotent に書き込み（DELETE → INSERT。部分失敗で既存スコアを残す戦略）。
  - テスト容易性: _call_openai_api などをパッチ差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動ETF）の直近200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する処理を実装。
  - prices_daily から ma200_ratio を計算（target_date 未満のみ使用してルックアヘッドを防止）。データ不足時は中立扱い（ma200_ratio=1.0）してフォールバック。
  - raw_news からマクロキーワードでフィルタした最新タイトルを取得し、OpenAI に送信して macro_sentiment を取得（記事が無ければ LLM 呼び出しをスキップして 0.0）。
  - OpenAI 呼び出しは独立実装で、エラー時のフォールバックやリトライ方針を明確化。
  - 最終的な regime_score をクリップしてラベル化し、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスで ETL 実行結果とメタ情報（取得数、保存数、品質問題、エラー）を格納・変換する仕組みを実装。
    - 差分更新・バックフィル・品質チェックの方針をコードに反映（最小日付、バックフィル日数、カレンダー先読みなど）。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無に応じた営業日の判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - calendar_update_job: J-Quants クライアントを使った差分取得と保存の夜間バッチ処理を実装。バックフィルと健全性チェック（極端な未来日付の検出）を備える。
  - jquants_client（参照）：ETL や calendar 更新のための外部クライアント呼び出しを想定（fetch / save 関数を利用）。

- 研究・分析モジュール（kabusys.research）
  - factor_research
    - Momentum ファクター（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等を DuckDB の SQL/ウィンドウ関数で実装。データ不足時は None を返す等の堅牢設計。
    - 各関数は prices_daily / raw_financials のみを参照し、本番取引や発注 API とは完全に切り離し。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度のクエリで取得するパフォーマンス設計。入力検証あり（horizons の範囲制約）。
    - IC（Information Coefficient）計算（calc_ic）：ファクター値と将来リターンのランク相関（Spearman ρ）を計算し、十分なサンプルがない場合は None を返す。
    - 統計サマリー（factor_summary）および rank ユーティリティを実装（同順位処理は平均ランク）。
  - research パッケージで主要関数を再エクスポート（利便性向上）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- OpenAI API キーの取り扱い:
  - 関数呼び出し時に api_key を明示的に注入可能（api_key 引数を優先）。デフォルトでは環境変数 OPENAI_API_KEY を利用。
  - api_key 未指定時は ValueError を発生させて意図しない静かなフェイルを防止。

Notes / Design decisions
- ルックアヘッドバイアス対策: ほとんどの処理で date / target_date を明示的に引数として受け、datetime.today()/date.today() を直接参照しない。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 方針等）して部分失敗で既存データを不意に消さない。
- OpenAI 呼び出しは JSON Mode を前提とし、レスポンスの余分な前後テキストに対しても復元を試みる（最外の {} を抽出するなど）。
- テストしやすさを重視: 外部 API 呼び出し部分（_call_openai_api など）を patch して差し替え可能に構成。

今後の予定（例）
- strategy / execution / monitoring パッケージの具体実装（実際の発注ロジック・実行エンジン・監視エージェント）。
- jquants_client の具体実装と ETL pipeline の実運用テスト強化。
- ai モジュールの評価精度改善、プロンプト調整とモデルスイッチ可能性の検討。

以上