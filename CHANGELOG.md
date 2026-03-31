# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- 開発中。主な機能は v0.1.0 にて初期公開済み。

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。以下は主要な追加点・設計上の注記です。

### Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py: バージョン情報と公開サブパッケージ（data, strategy, execution, monitoring）の定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - OS 環境変数を保護するための protected キー判定（.env.local は既存 OS 環境変数を上書きしない）。
    - 必須変数取得時に未設定で ValueError を送出する _require。
    - 設定オブジェクト Settings （J-Quants トークン、kabu API、Slack、DB パス、環境種別・ログレベル検証など）。
    - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。

- AI（自然言語処理）関連
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を使ったニュース集約（銘柄ごとに最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出して銘柄ごとのセンチメントスコアを生成。
    - バッチ処理（1コールあたり最大20銘柄）、レスポンス検証（results 配列の構造検査、コード照合、数値検証）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを消さないための部分置換（DELETE → INSERT）ロジック。
    - テスト容易性を考慮した _call_openai_api の差し替えポイント。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換して扱う）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio（ルックアヘッド対策で target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - マクロニュース抽出（マクロキーワードによるフィルタ）と OpenAI 呼び出し（gpt-4o-mini、JSON Mode、リトライ/フォールバック）。
    - レジームスコア計算、ラベリング閾値（BULL/BEAR）設定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キー注入可（api_key 引数または環境変数 OPENAI_API_KEY）。API 失敗時は macro_sentiment=0.0 で継続。

- データ基盤（DataPlatform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブルの参照/更新、営業日判定、前後営業日の計算、期間内営業日の取得、SQ日判定）。
    - DB 登録がない日や NULL 値に対する曜日ベースのフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存。バックフィルと健全性チェックを実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラス（取得/保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分取得・保存・品質チェックの設計に準拠した ETL パイプラインの基礎（J-Quants クライアント連携、バックフィル、idempotent 保存）。
    - DuckDB 互換性への配慮（executemany に空リスト不可等のハンドリング）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、カレンダーヘルパー）を実装。

- リサーチ（研究）機能
  - src/kabusys/research/*
    - factor_research.py: Momentum / Volatility / Value 等のファクター計算（mom_1m/3m/6m、ma200_dev、atr_20、avg_turnover、per、roe 等）。
      - DuckDB SQL を駆使した実装。データ不足時は None を返す。結果は (date, code) をキーとする dict のリストで返却。
    - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を提供。
      - calc_forward_returns は任意ホライズンに対応（horizons 検証あり）。
      - calc_ic はスピアマン（ランク相関）を計算し、サンプル数不足時は None。
    - research パッケージ __init__ でユーティリティをエクスポート（zscore_normalize などの再エクスポート含む）。

### Changed
- （初回リリースのため該当なし）設計上の決定・方針はモジュールドキュメンテーション内に明記（例: ルックアヘッドバイアス回避のため datetime.today() を直接参照しない等）。

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数取得は必須項目に対して明確に検証を行い、未設定時は ValueError を発生させる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
- OS 環境変数を優先・保護する設計によりテスト時に意図しない上書きを防止。

### Notes / 実装上の重要事項
- OpenAI との連携は gpt-4o-mini（JSON mode）を想定。レスポンスパースに失敗した場合は安全側へフォールバック（スコア = 0.0 または該当銘柄スキップ）。
- テスト容易性のため各モジュールで API 呼び出し関数を差し替えられるよう設計（unittest.mock.patch による置換を想定）。
- DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、部分失敗時に他データを守る実装（例: ai_scores の部分DELETE/INSERT）。
- DuckDB のバージョン互換性（executemany の空リスト不可等）に配慮したコードパスを含む。
- 日付および時間は明示的に date/datetime オブジェクトで扱い、timezone 混入を避ける方針。

### Known limitations / 今後の改善候補
- News NLP / Regime Detector の LLM 呼び出しは現在 JSON Mode のパースに依存しているため、将来的な API 仕様変更に対するラッパーの強化が必要。
- ファクターモジュールには PBR・配当利回りなど未実装の指標があり、拡張の余地あり（calc_value の注記参照）。
- ETL 周りで J-Quants クライアント（jquants_client）実装に依存する箇所があるため、ローカルテスト用スタブ/モックの整備が望ましい。

---

（このCHANGELOGはコードの実装内容とモジュールドキュメント文字列から推測して作成しています。実際のリリースノート作成時は変更差分・コミット履歴に基づく精査を行ってください。）