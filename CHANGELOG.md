# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはリポジトリ内のコードを解析して推測した初期リリース向けの変更履歴です。

全体方針:
- バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。
- 設計方針やフェイルセーフ、テスト容易性に関する注記は実装コメントから反映しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。日本株のデータ取得・ETL・ファクター計算・ニュースNLP・市場レジーム判定を中心とした基盤機能を提供します。

### Added
- パッケージ基盤
  - パッケージメタ情報の公開（src/kabusys/__init__.py）。
  - settings オブジェクト経由での環境変数アクセス（src/kabusys/config.py: Settings）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出、.env / .env.local の適切な優先度）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等をサポート。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの結果データクラス ETLResult を公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
  - 差分更新・バックフィル・品質チェックを想定した ETL 設計（バックフィル日数・カレンダー先読み等を設定可能）。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar テーブルの存在チェック、営業日判定、翌/前営業日検索、期間内営業日取得、SQ判定などの API を提供。
    - DBにデータがない場合は曜日ベースでフォールバック（週末は非営業日）する堅牢な挙動。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェックあり）。
  - DuckDB との安全なトランザクション制御と部分書込み戦略（DELETE → INSERT、executemany の空リスト回避）。

- リサーチ機能
  - ファクター計算群（src/kabusys/research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などを計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から算出。
    - 設計上、prices_daily / raw_financials のみ参照し、本番発注系 API に影響しない構成。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank, factor_summary: ランク化ユーティリティと統計サマリを提供。
    - 外部ライブラリ（pandas 等）に依存しない実装。

- AI（ニュースNLP / レジーム判定）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を用い、銘柄ごとに前日15:00 JST〜当日08:30 JST の記事を集約して OpenAI（gpt-4o-mini）へバッチ送信。
    - 1チャンク最大20銘柄、1銘柄あたり最大10記事・最大3000文字でトリム。
    - JSON Mode を利用し厳格な JSON レスポンスを想定、レスポンスのバリデーション・数値クリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - テスト容易性のため _call_openai_api をモック差替え可能に設計。
    - calc_news_window を公開（タイムウィンドウ計算）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime を日次で生成。
    - マクロニュースは raw_news からキーワードフィルタ（複数キーワード）で抽出し、OpenAI で macro_sentiment を算出。
    - LLM 呼び出しはリトライ/フェイルセーフを実装（API失敗時は macro_sentiment=0.0 で継続）。
    - DB 書き込みは冪等に行う（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出し実装を news_nlp とは独立して持ち、モジュール結合を避ける設計。
  - AI 機能は api_key（引数または環境変数 OPENAI_API_KEY）が必要であり、未設定時は ValueError を投げる。

- ロギング・堅牢性
  - 多数の箇所で警告/情報ログ出力を実装し、フェイルセーフやデータ不足時の既定値（例: ma200_ratio=1.0）を定義。
  - DuckDB の executemany に関する互換性考慮（空リストを渡さないチェック）を実装。

- テスト/デバッグ配慮
  - OpenAI 呼び出し箇所で差し替え可能な内部ラッパーを採用（unittest.mock.patch でのモックを想定）。
  - 環境変数ロードはプロジェクトルート検出を行い、実行カレントディレクトリに依存しないように設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用。機能を利用する際はキーの取り扱いに注意してください。
- .env 自動ロードはデフォルトで有効だが、テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

## 既知の制約・注意事項
- OpenAI 依存機能（news_nlp, regime_detector）は API 利用料や利用制限の影響を受けます。ローカルテストでは _call_openai_api をモックしてください。
- DuckDB のバージョン差異により executemany の挙動が異なるため、空パラメータの送出を避ける実装になっています。
- ai モジュールは gpt-4o-mini の JSON mode を前提にしており、LLM 応答が厳密な JSON でない場合でも復元ロジックを実装していますが、完全な保証はありません。
- 一部の関数は「ルックアヘッドバイアス」を防ぐために現在時刻参照（date.today() や datetime.today()）を使用しない設計です。必ず target_date を呼び出し側で渡す必要があります。

---

（注）本 CHANGELOG はコード内容から機能・設計方針を推測して作成しています。実際のリリースノートやプロジェクト戦略に合わせて適宜修正してください。