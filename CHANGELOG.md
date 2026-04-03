Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは "Keep a Changelog" の形式に従います。

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基盤的モジュールを追加。
  - パッケージ情報
    - kabusys.__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - 設定 / 環境変数管理（kabusys.config）
    - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。
      - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して解決。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 読み込み順: OS 環境変数 > .env.local > .env。.env.local は .env を上書きする。
      - OS 環境変数は protected として上書きを保護。
    - .env パーサを実装（kabusys.config._parse_env_line）。
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープを処理。
      - クォートなし行ではインラインコメント（#）をスペース/タブ直前のみコメントと認識。
    - Settings クラスを提供（settings インスタンス経由で利用）。
      - J-Quants / kabu ステーション / LINE API / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを提供。
      - env と log_level の値検証を実装（不正値は ValueError）。
      - ファイルパスは Path 型で返却（expanduser を使用）。
      - 必須環境変数取得時のエラー報告を実装（_require）。
  - AI 関連（kabusys.ai）
    - news_nlp モジュール（kabusys.ai.news_nlp）
      - raw_news と news_symbols を集約して、OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ書き込む。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して利用。
      - バッチ処理: 最大 20 銘柄/API コールで処理（_BATCH_SIZE=20）。
      - 1銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
      - JSON Mode を利用し、レスポンスを厳密に検証（results 配列、code/score の検査、数値チェック、±1.0 でクリップ）。
      - リトライ設計: 429、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ（デフォルト上限含む）。
      - API 呼び出しはテスト時に差し替え可能（内部関数 _call_openai_api を patch して置換）。
      - DB 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存スコアを保護。
      - フェイルセーフ: API 失敗や検証失敗時は該当チャンクをスキップし、全体処理を継続。
    - regime_detector モジュール（kabusys.ai.regime_detector）
      - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
      - MA 計算は target_date 未満のデータのみ使用してルックアヘッドを防止。
      - マクロニュースは定義したキーワードでフィルタリングし、LLM（gpt-4o-mini）に渡して JSON 出力を期待。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
      - API 呼び出しのリトライ・5xx の扱いなど堅牢化を実装。最終的に score をクリップしてラベル化。
      - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行。エラー時は ROLLBACK を試行。
      - テスト用に _call_openai_api を差し替え可能。
  - データ処理（kabusys.data）
    - calendar_management
      - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
      - DB にデータがない・未登録日については曜日ベース（土日非営業）でフォールバック。DB 登録値が優先。
      - カレンダー夜間バッチ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し保存。バックフィルや健全性チェック（将来日付の異常検出）を実装。
    - ETL / pipeline
      - ETLResult データクラスを導入（kabusys.data.pipeline.ETLResult）。取得件数・保存件数・品質問題・発生エラーを集計して返却。
      - ETL 実装の設計方針を反映（差分更新、バックフィル、品質チェック結果の集約、idempotent 保存）。
      - _table_exists / _get_max_date などのユーティリティを追加。
    - etl モジュール
      - pipeline.ETLResult を再エクスポートして公開インターフェースを整備。
    - jquants_client（参照）を用いた保存/取得処理を想定（実装は別モジュールとして分離）。
  - 研究用ユーティリティ（kabusys.research）
    - factor_research
      - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB のウィンドウ関数を活用し、営業日・ウィンドウ緩衝を考慮した実装。
      - データ不足時は None を返す設計（安全性重視）。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証あり）。
      - IC（Information Coefficient）計算（calc_ic: スピアマン ρ をランクにより算出、サンプル不足時に None を返す）。
      - ランク変換ユーティリティ（rank: 同順位は平均ランク）。
      - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median を計算）。
    - research パッケージは研究用途に限定し、本番発注 API 等にはアクセスしない方針を明記。
  - その他
    - モジュールごとにログ出力とデバッグ用メッセージを充実。
    - DuckDB を主要なオンディスク分析 DB として利用する想定で SQL を記述。

Changed
- N/A（初回リリースのため履歴上の変更なし）。

Fixed
- N/A（初回リリースのため修正履歴なし）。

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。API キー取得時は明示的に未設定エラーを返すことで誤設定を検出しやすくしている。

Notes / 実装上の注意点
- ルックアヘッドバイアス防止のため、いずれのモジュールも内部で datetime.today()/date.today() をデフォルト参照せず、明示的な target_date を受け取る設計です。
- OpenAI への呼び出しは現時点で gpt-4o-mini を想定。JSON Mode を使った応答パースのため、レスポンスのパース失敗や不正レスポンスに対するフォールバックロジックを備えています。
- テスト容易性のため、内部の API 呼び出し関数（_call_openai_api 等）を unittest.mock.patch 等で差し替え可能にしてあります。
- DuckDB のバージョン差異（executemany の空リスト扱いなど）を考慮した実装上のガードを入れています。

今後の予定（例）
- jquants_client の実装/統合・自動 ETL スケジューリングの整備
- モデル／閾値のチューニングや追加のファクター実装
- 単体テスト・統合テストの追加と CI パイプライン整備

---