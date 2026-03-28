# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" のフォーマットに従います。  

- リリースノートは semver 準拠です（このパッケージのバージョンは src/kabusys/__init__.py の __version__ に合わせてください）。

## [Unreleased]

---

## [0.1.0] - 2026-03-28

初回公開リリース: 日本株自動売買システムの基盤機能群を実装・公開しました。以下はコードベースから推測される主な追加機能・設計上のポイントです。

### Added
- パッケージ基盤
  - パッケージバージョン管理を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API を定義（__all__ に "data", "strategy", "execution", "monitoring" を設定）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込むユーティリティを実装。
  - 自動読み込みの優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env のパース処理を堅牢化（export プレフィクス対応、シングル/ダブルクォート内のエスケープ、インラインコメント対応）。
  - 環境変数上書き制御（override, protected set）。
  - Settings クラスを提供し、required な環境変数取得（_require）と各種設定プロパティを公開：
    - J-Quants・kabu・Slack・DB パス等の必須/デフォルト値
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理 / レジーム検出）
  - ニュース NLP（kabusys.ai.news_nlp）
    - ニュース記事を OpenAI（gpt-4o-mini, JSON Mode）でバッチ処理し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ算出（JST ベース → UTC naive datetime）を提供（calc_news_window）。
    - 記事の銘柄単位集約、トリム（記事数・文字数制限）を実装。
    - バッチサイズ・リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）・レスポンス検証の実装。
    - レスポンスの堅牢な JSON パースとバリデーション、スコアの ±1.0 クリップ。
    - DuckDB 互換性を考慮した安全な DB 書き換え（部分置換: DELETE→INSERT、executemany の空リスト回避）。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド回避のため target_date 未満のみ使用、データ不足時は中立 1.0 を返す）。
    - マクロニュース抽出（キーワードによるフィルタ、最大記事数制限）、OpenAI 呼び出し、再試行ロジックを実装。
    - 結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK を試行。
    - API 失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由の差分取得 → 保存）。
    - 営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録がない場合は曜日ベースのフォールバック（週末を休日扱い）を提供。
    - 最大探索範囲・バックフィル・健全性チェックを備えた堅牢な設計。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（ETL 実行結果の構造化、品質問題・エラーの集約）。
    - 差分取得・バックフィル・品質チェックを想定したユーティリティと DB 最大日付取得等の補助関数を実装。
    - ETLResult を kabusys.data.etl で再エクスポート。
  - DuckDB を前提としたクエリ／互換性配慮（date 型変換ユーティリティ等）。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB での SQL ベース実装（prices_daily, raw_financials を参照）。データ不足時の None ハンドリング。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）の算出（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 依存を避けた純 Python 実装、入力レコード形式は辞書リスト。

- その他
  - OpenAI クライアント利用に関して、API キー注入（引数 or OPENAI_API_KEY 環境変数）をサポート。
  - ロギングと警告出力を多用し実行時の状況把握を容易にする設計。
  - ルックアヘッドバイアス対策を徹底（datetime.now()/date.today() を処理基準に直接使わない方針）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 外部 API（OpenAI, J-Quants）キーは環境変数経由の注入を想定し、直接埋め込みを避ける設計。

### Notes / Implementation details / Design decisions
- DuckDB を DB 層に利用。executemany の挙動や日付型の取り扱いなど DuckDB の特性を考慮した実装が多く含まれます。
- OpenAI 呼び出しは JSON Mode を利用して厳密な JSON を期待するが、前後余計なテキストが混ざるケースに備えたパース回復ロジックを入れている。
- テストの容易性を考慮し、外部呼び出し箇所（OpenAI 呼び出し等）はモック差し替えを前提に設計されています。
- DB 操作は冪等性を重視（DELETE→INSERT や ON CONFLICT 相当の保存を想定）しているため、部分失敗時の既存データ保護が図られている。

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装詳細（発注ロジック、リスク制御、リアルタイム監視）、より細かい品質チェック・テストカバレッジ、ドキュメントの補完などが想定されます。必要であればこの CHANGELOG を英語版で作成したり、各モジュールごとの変更点をより詳細に分割したエントリを作成します。