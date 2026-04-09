# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（現状なし）

## [0.1.0] - 2026-04-09

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買・データ基盤・リサーチ用ユーティリティ群を追加。
- パッケージメタ:
  - バージョン番号を src/kabusys/__init__.py にて "0.1.0" として公開。
  - パブリックサブパッケージの __all__ に data, strategy, execution, monitoring を設定。

- 設定・環境変数管理（kabusys.config）:
  - .env ファイル（.env, .env.local）および OS 環境変数の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する .env パーサを実装（堅牢なパース処理）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティを公開。
  - 必須キー未設定時の明示的エラー（_require）や、PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を実装。
  - デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db" などを設定。

- AI モジュール（kabusys.ai）:
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を実行。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり最大記事数・文字数制限、レスポンス検証と ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時は安全にスキップするフェイルセーフ設計。
    - calc_news_window により JST ベースのニュース収集ウィンドウを正確に算出（ルックアヘッド防止）。
    - API 呼び出し箇所をテストで差し替え可能（_call_openai_api を patch 可能）。
    - 書き込みは部分失敗時に既存データを保護する方針（対象コードのみ DELETE → INSERT）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - OpenAI クライアントは引数の api_key または環境変数 OPENAI_API_KEY で決定。
    - DB 書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行して上位へ例外を伝播。

- Data（kabusys.data）:
  - calendar_management:
    - JPX カレンダー管理（market_calendar）: 営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバックする堅牢な挙動。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性チェックを行い、冪等に保存。
  - pipeline / ETL:
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー集約等を保持、to_dict を提供）。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast ではなく呼び出し元判断）を採用。
  - etl モジュールで ETLResult を再エクスポート。

- Research（kabusys.research）:
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の扱いを明示）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。
    - すべて DuckDB 上の SQL + Python で実装し、本番 API へのアクセスは一切行わない設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を効率的に取得する SQL 実装（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足時は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を実装（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 研究用 API は外部ライブラリ（pandas 等）に依存せず、標準ライブラリと DuckDB のみで動作。

- ロギング・堅牢性:
  - 各モジュールで詳細な logger 出力を追加（info/debug/warning/message）。
  - DB トランザクションでの例外時に ROLLBACK を試行し、ROLLBACK 自体の失敗も警告ログで報告。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() の不適切な参照を避ける設計を明記。

### Changed
- （初期リリースのため変更履歴はなし）

### Fixed
- （初期リリースのため修正履歴はなし）

### Security
- OpenAI API キーは明示的に引数で注入可能（テスト容易性）、未設定時は ValueError を発生させる安全な扱い。

---

注記:
- OpenAI のモデルは gpt-4o-mini を使用する想定で実装しています。  
- 一部モジュールは外部クライアント（jquants_client など）へ依存しますが、クライアント実装は別モジュールで提供される想定です。  
- 本 CHANGELOG は提供されたコードから推測して作成しています。実際のリリースノートと差異がある場合は適宜修正してください。