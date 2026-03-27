# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-27

最初の公開リリース。日本株自動売買システムのコア機能群を実装しました（パッケージ名: kabusys, __version__ = 0.1.0）。

### Added
- パッケージ初期構成
  - パッケージエントリポイント（src/kabusys/__init__.py）を追加し、data/strategy/execution/monitoring を公開。
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサ実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理をサポート）。
  - override/protected 機構により OS 環境変数を保護して .env による上書きを制御可能。
  - Settings クラスを提供（必須トークン取得関数 _require を含む）。
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル検証（許容値チェック）などをプロパティで取得。
    - is_live / is_paper / is_dev ヘルパを実装。
- AI 関連機能（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）にバッチ送信してセンチメントを ai_scores に保存。
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ・記事数・文字数トリム制限を設け、トークン肥大化を抑制。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密検証（JSON 抽出、results 配列、コード整合性、数値検証、スコア ±1.0 クリップ）。
    - DuckDB の executemany の挙動を考慮した空リストチェック（互換性対策）。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - マクロキーワードによる raw_news フィルタ、LLM 呼び出し（gpt-4o-mini、JSON mode）、リトライ、フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK ハンドリング）。
- Research（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、売買代金等）、Value（PER, ROE）ファクターを実装。
    - DuckDB SQL を活用し prices_daily / raw_financials のみ参照して計算。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンの順位相関）と rank ユーティリティ（同順位は平均ランク、丸めで ties の安定化）。
    - factor_summary による基本統計量集計。
  - research パッケージ初期エクスポートを提供。
- Data（src/kabusys/data/*）
  - 市場カレンダー管理（calendar_management.py）
    - market_calendar を元に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録がない場合は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得→保存（バックフィル・健全性チェック・例外ハンドリングを含む）。
  - ETL パイプライン（pipeline.py）
    - ETL の設計に基づくユーティリティ関数群と ETLResult データクラスを実装。
    - ETLResult は取得件数・保存件数・品質問題・エラー一覧を保持し、has_errors / has_quality_errors / to_dict を提供。
    - 差分取得・バックフィル・品質チェック方針を反映した内部ユーティリティ（_get_max_date 等）を実装。
  - etl モジュールから ETLResult を再エクスポート。
  - jquants_client との連携を想定したインターフェース呼び出しを多数利用（fetch/save 関数の利用箇所を準備）。
- 共通の設計方針と安全対策
  - ルックアヘッドバイアス防止: 各処理は内部で datetime.today()/date.today() を直接参照しない（target_date ベースで動作）。
  - OpenAI / 外部 API 呼び出しのフォールバック: API 失敗時に全体停止させず、フェイルセーフ（スコア 0.0 を採用、部分的にスキップ）で継続可能。
  - DB 書き込みはトランザクションで行い、例外時には ROLLBACK を試行（失敗時は警告ログ）。
  - ロギングを各所に追加し、処理の可観測性を向上。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- .env 読み込み時に OS 環境変数を protected として保護する仕組みを導入（重要な外部トークンが .env で誤って上書きされないようにする）。
- 必須環境変数未設定時は明確な ValueError を発生させ、早期に検出可能に。

### Notes / Known limitations
- OpenAI API キー未設定時は明示的に例外を投げる（score_news / score_regime）。テストでは api_key 引数や環境変数を注入して使用してください。
- DuckDB のバージョン差異に起因する executemany の空リストバインド問題に対処するため、空チェックを行っている。
- PBR・配当利回りなど一部ファクターは未実装（calc_value では将来的に拡張予定）。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール結合を避けています。テスト時は個別にモックしてください。

---

今後のリリースでは、テストカバレッジの拡充、scheduler/CLI の追加、strategy と execution の結合、より多くのファクタ拡張と品質チェック強化を予定しています。