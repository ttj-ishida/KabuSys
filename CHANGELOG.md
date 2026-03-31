# Changelog

すべての重要な変更履歴は Keep a Changelog の形式に準拠して記載します。  
このプロジェクトの初回公開リリースを以下に示します。

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。パッケージメタ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring

- 環境変数／設定管理モジュール (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサー実装: export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理など。
  - Settings クラス提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）, Slack トークン／チャンネル、DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）やログレベルのバリデーション。
  - 必須キー未設定時は ValueError を送出する _require 実装。

- AI モジュール (src/kabusys/ai)
  - news_nlp（ニュースのセンチメント解析、score_news を公開）
    - OpenAI（gpt-4o-mini）の JSON Mode を利用したバッチ評価機能。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して照合）。
    - 銘柄ごとの記事集約、記事数と文字数のトリム制御（上限値実装）。
    - バッチサイズ・リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ。
    - レスポンスの厳密なバリデーションと ±1.0 のクリップ、部分成功時の DB 書き換えロジック（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を差し替えられる設計。
  - regime_detector（市場レジーム判定、score_regime を公開）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）、API障害時は macro_sentiment=0.0 でフォールバック。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス防止のため、日付に対して過去データのみを参照する実装方針。

- Data / ETL / カレンダー / パイプライン機能 (src/kabusys/data)
  - pipeline.ETLResult を公開（ETL 実行結果の dataclass）。
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブル操作、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB が存在しない／データがない場合の曜日ベースフォールバック。
    - calendar_update_job: J-Quants から差分取得→保存、バックフィル・健全性チェック実装。
    - 最大探索日数や先読み／バックフィル日数の定数化。
  - pipeline（ETL 実装基盤）
    - 差分更新、保存（jquants_client 経由で冪等保存）、品質チェックの収集方針を定義。
    - ETLResult に品質チェックとエラー集約の仕組みを実装。

- Research モジュール (src/kabusys/research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）ファクター計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL + Python 実装、データ不足時の None 扱い、結果は (date, code) キーの dict リストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - 外部依存を持たない純標準ライブラリ実装、horizons パラメータ検証、ランクは同順位を平均ランクで扱う。

- パッケージ構造上のユーティリティ
  - ai/__init__.py で score_news を公開。
  - research/__init__.py で主要関数を再エクスポート。
  - data/etl.py で ETLResult を再エクスポート。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- 初版リリースのため該当なし。

### Notes / 既知の挙動と設計上の注意
- OpenAI API を使用する機能（score_news, score_regime）は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- LLM 呼び出しはリトライやフォールバックを行うが、API の結果不整合時は該当レコードをスキップし処理を継続する設計（フェイルセーフ）。
- 日付の扱いはルックアヘッドバイアス防止のため、関数内部で datetime.today()/date.today() を直接参照しない実装方針を採用（target_date を明示的に渡す）。
- DuckDB に対する executemany の空リスト制約（0.10 系）に対処した実装（空の場合は実行しない）。
- .env パーサーは複数の形式に耐性あり（export プレフィックス、クォート・エスケープ、行内コメントなど）。
- テスト容易性: OpenAI 呼び出し部分は内部ヘルパー関数（_call_openai_api）を patch/モックできるよう設計。

---

今後のリリースでは、次のような追加・改善が考えられます（未実装/検討中）:
- strategy / execution / monitoring パッケージの実装（発注ロジック・モニタリング連携）。
- AI モデルの選択肢拡張・プロンプトチューニング、より堅牢なレスポンス検証。
- jquants_client の実装詳細に依存するテストカバレッジとモックユーティリティの追加。
- ドキュメント（Usage、API、設定手順）の充実。