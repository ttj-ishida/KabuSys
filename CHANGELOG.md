Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- 開発中の変更・TODOなどをここに記載します。

[0.1.0] - 2026-03-27
-------------------

Added
- 初期リリース: KabuSys v0.1.0 を公開。
- パッケージ基盤
  - パッケージ初期化ファイルを追加（kabusys.__version__ = "0.1.0"）。
  - モジュール公開（data, strategy, execution, monitoring のエクスポート準備）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に self-contained に探索。
  - .env パーサーを実装:
    - export KEY=val 形式の対応。
    - シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - コメント行・空行のスキップ。
  - .env の読み込み順序と上書きルール:
    - 優先度: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護する protected 機構を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供し、主要設定をプロパティで取得:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/ 環境（development/paper_trading/live）/ログレベル検証など。
    - 未設定の必須値は ValueError を送出する明確なエラー。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - ニュースの時間ウィンドウ計算 (calc_news_window)。
    - raw_news と news_symbols を集約して銘柄ごとにテキストをまとめ、OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込む score_news を実装。
    - バッチ処理、1チャンクあたり最大銘柄数、文字数制限、JSON Mode での応答処理、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存データを保護する置換ロジック（DELETE → INSERT）を実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - レスポンスパース失敗時や API 失敗時はフェイルセーフでスキップ（例外を投げず中断を回避）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの MA 計算、raw_news からのマクロ記事抽出、OpenAI 呼び出し（JSON 出力想定）とリトライ、レジームスコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ、API 呼び出しは別実装としてモジュール間結合を避ける設計。

- データ処理 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理: market_calendar を元に営業日判定、前後営業日取得、期間内営業日リスト取得、SQ 判定などのユーティリティを実装。
    - market_calendar 未取得時は曜日ベース（土日非営業）でのフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル、健全性チェック付き）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約：取得数、保存数、品質チェック結果、エラー一覧など）。
    - ETL の差分取得・保存・品質チェックのための基盤を実装（jquants_client 経由で Idempotent 保存を想定）。
  - DuckDB との互換性および実運用上の注意点（executemany の空リスト対策など）を考慮した実装。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。すべて DuckDB SQL で計算し、(date, code) をキーにした dict リストを返す。
    - 指標: 1M/3M/6M リターン、200 日 MA 乖離、20 日 ATR、平均売買代金、出来高比率、PER/ROE など。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターン算出）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（統計サマリー）、rank（平均ランク付与）を実装。
    - pandas 等の外部依存なしで標準ライブラリ／DuckDB を使用。

- 設計上のポリシー（ドキュメント化）
  - ルックアヘッドバイアス防止のため、主要アルゴリズムで datetime.today()/date.today() を直接参照しない設計を徹底。
  - API 呼び出し失敗時は中立値やスキップで安全に継続するフェイルセーフ方針。
  - テスト容易性のため外部呼び出し箇所は patch 可能に実装（内部 _call_openai_api 等）。

Fixed
- .env パーサーの堅牢化:
  - クォート内部のバックスラッシュエスケープ処理、クォート終了位置判定、クォートなしのコメント解釈（直前がスペース／タブの場合のみ '#' をコメント扱い）などを取り込んで、実運用でよくある .env の書き方に対応。

Security
- 環境変数読み込みで OS 環境を上書きしないデフォルト動作と、明示的に上書きを有効にするオプションを用意。重要な OS 環境変数を保護する設計。

Notes / 附記
- OpenAI クライアントは gpt-4o-mini を指定し、JSON Mode を使ったレスポンス想定の上でパース耐性を持たせている（前後の余計なテキストを取り除くロジック等）。
- DuckDB を主要な分析・保存用エンジンとして想定。SQL 内でウィンドウ関数や行数チェックを多用している。
- ai_scores / market_regime 等の DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。
- 一部の内部関数（例: _call_openai_api）をテスト時に差し替えることを前提とした API 設計。

今後の予定（例）
- strategy / execution / monitoring 各モジュールの実装と統合テスト。
- J-Quants / kabu API クライアントの実装補完・認証フロー整備。
- CI による DuckDB ベースの自動テスト、モック OpenAI の導入。