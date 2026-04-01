# CHANGELOG

すべての重要な変更をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

注: 以下の変更点は、与えられたコードベース（src/kabusys/…）の内容から推測して記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買システムの基盤となるモジュール群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本エクスポートを追加（data, strategy, execution, monitoring）。
  - バージョン情報: 0.1.0。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定は .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env のパースは export 文、シングル/ダブルクォート、エスケープ、インラインコメント（クォート無しでの # の扱い）に対応。
  - 自動ロード無効化用変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB（DuckDB/SQLite） パス / 監視設定（PID, CPU/Mem/Disk閾値）/ 環境（development/paper_trading/live）/ログレベル判定など。
    - 必須キー未設定時は ValueError を送出する _require() を用意。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄別テキストを作成し、OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信してスコアを取得。
    - JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換して対象記事を抽出する calc_news_window を実装。
    - バッチサイズ、記事数・文字数制限、レスポンス検証と ±1.0 クリップ、リトライ（429/ネットワーク/5xx）や指数バックオフを実装。
    - DuckDB executemany の空リスト制約を考慮して、書込み前に空チェックを行う。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュース抽出のためのキーワード群、タイトル取得、OpenAI 呼び出し（gpt-4o-mini）を備える。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックする堅牢な実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止設計（date 引数ベース、today を直接参照しない）。

- データ処理（kabusys.data）
  - マーケットカレンダー管理（data.calendar_management）
    - market_calendar を使った営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。DB 登録値を優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）。
    - 検索範囲制限（最大探索日数）やバックフィル、将来日付の健全性チェックを実装。
  - ETL パイプライン（data.pipeline / data.etl）
    - ETLResult データクラスを公開（取得数 / 保存数 / 品質チェック結果 / エラー等を格納）。
    - 差分更新・バックフィル・品質チェックを想定した ETL 設計（jquants_client 経由での保存、品質チェック収集、idempotent 保存）。
    - 内部ユーティリティとしてテーブル存在確認・最大日付取得等を実装。
  - jquants_client の利用を前提としたデータ取得/保存の設計（実装ファイルはコード内で参照）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Volatility（20日 ATR, ATR/価格 比, 20日平均売買代金, 出来高比率）
    - Value（PER, ROE。raw_financials からの最新財務データ利用）
    - DuckDB を用いた SQL ベースの計算、データ不足時の None ハンドリング
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns: 複数ホライズンを一括取得）
    - IC（Information Coefficient, Spearman の ρ）計算（calc_ic）
    - ランク変換ユーティリティ（rank）
    - ファクター統計サマリー（factor_summary）
    - pandas 等の外部依存無しの純 Python 実装を志向

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Security
- OpenAI API キーおよび各種機密情報は環境変数経由で管理。必須キー未設定時は明示的にエラーを発生させる設計。

### Notes / Limitations
- OpenAI 連携
  - デフォルトモデルは gpt-4o-mini。API 呼び出しは JSON Mode を利用する想定。
  - API エラー・パースエラーはフェイルセーフ（スコア 0.0 やスキップ）で動作するため、部分失敗時でも処理継続が可能。
  - テストのため _call_openai_api を差し替え可能に設計している（unittest.mock.patch）。
  - OpenAI API キーは api_key 引数で注入可能（テストや一時的上書き用）。未指定時は環境変数 OPENAI_API_KEY を参照。

- DuckDB 互換性
  - executemany に空リストを渡すと失敗するバージョン (DuckDB 0.10) を考慮して空チェックしている箇所あり。

- ルックアヘッド対策
  - ニュース / レジーム / ファクター系処理はいずれも内部で date 引数を使用し、datetime.today()/date.today() を直接参照しない設計になっている。

- 未実装 / 今後の作業
  - strategy, execution, monitoring モジュールの詳細実装や jquants_client の実装はこのスナップショットからは推測不可（参照はあるがファイル未提示）。
  - 一部のエッジケース（極端なカレンダー欠損や API の大規模障害）に対するオペレーション手順のドキュメント化が必要。

---

(この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに基づく更新を推奨します。)