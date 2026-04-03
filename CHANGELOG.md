# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、慣例に従ってセクションを分けています。

最新: [Unreleased] → 安定版リリースは下の履歴を参照してください。

## [Unreleased]

（現在なし）

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォームの基盤機能群を実装しました。主な追加点と設計上の注記は以下の通りです。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ でエクスポート）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git / pyproject.toml を探索）によりカレントワーキングディレクトリに依存しない自動読み込みを実現。
  - .env と .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）を実装。既存 OS 環境を保護するため protected キー集合を保持。
  - export KEY=val 形式、クォート・エスケープ、インラインコメント処理などを考慮した .env パーサを実装。
  - 自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル判定など）。
  - 必須環境変数未設定時に ValueError を投げる _require 実装。

- データ層（kabusys.data）
  - ETL パイプラインの基本構造（kabusys.data.pipeline）と ETLResult データクラスを提供。ETL 実行結果・品質問題・エラー集約をサポート。
  - market_calendar（マーケットカレンダー）管理モジュール（calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを実装。
    - DB が未取得の場合は曜日ベースのフォールバック（週末非営業日）を採用。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（fetch + save）を実装。バックフィル・健全性チェックを含む。
  - ETL 用ユーティリティ（etl.py）で ETLResult を再エクスポート。

- 研究・ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）の計算機能を実装。
    - DuckDB のウィンドウ関数を活かした SQL 主導の実装。データ不足時は None を返す挙動。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）を実装。
    - IC（Information Coefficient）計算（スピアマンランク相関）（calc_ic）。
    - ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
  - research パッケージの公開 API を整備（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- AI ニュース解析（kabusys.ai）
  - ニュースセンチメント解析（news_nlp）:
    - raw_news / news_symbols を集約して銘柄ごとのテキストを構築し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - 入力トリミング（記事数・文字数制限）、バッチサイズ制御、JSON Mode を使った応答処理を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフのリトライ、レスポンス検証（JSON 抽出・構造バリデーション・既知コードチェック・数値チェック）を実装。
    - スコアを ±1.0 にクリップ。部分成功時は対象コードのみ DELETE→INSERT することで既存データ保護。
    - calc_news_window（JST ベースの時間ウィンドウ算出）を実装（前日 15:00 JST 〜 当日 08:30 JST）。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily からの MA 計算、raw_news によるマクロキーワード抽出、OpenAI 呼び出し（独自実装）とスコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
  - AI 関連関数（score_news, score_regime）で OpenAI API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。未設定時は ValueError を送出。

### Changed
- （初版リリースのため過去版からの変更なし）

### Fixed
- （初版リリースのためバグ修正履歴なし）
- 実装上の堅牢性に関する注意:
  - DuckDB の executemany に空リストを渡すと失敗する点に対応し、空の場合は呼び出しをスキップする実装を行った（news_nlp / pipeline）。
  - OpenAI レスポンスの JSON パースにおいて前後に余計なテキストが混ざるケースを考慮し最外の {} を抽出して復元する処理を追加（news_nlp）。
  - DB 書き込み失敗時に ROLLBACK を試み、失敗ログを残すように実装（regime_detector / news_nlp）。

### Security
- 環境変数読み込み時、既存の OS 環境を保護するため protected キー集合を保持し .env による上書きを制御。
- API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を使用。未設定時は早期にエラー通知。

### Notes / 設計方針
- ルックアヘッドバイアス防止のため、date.today()/datetime.today() をスコープ内で直接参照せず、すべてのスコア算出・ウィンドウ計算は呼び出し元から与えられる target_date に基づく設計。
- 外部 API 呼び出し（OpenAI / J-Quants）はフェイルセーフを前提にし、API 失敗時は処理をスキップまたは中立値で継続する方針。
- DuckDB を主要なデータ格納・クエリ基盤として利用。SQL ウィンドウ関数を多用して高効率な集計を実装。
- 本リリースは「データ取得・加工・研究・AI スコアリング」の基盤を提供し、将来的に strategy / execution / monitoring 周りの実装拡張を想定。

---

（貢献者）
- 実装: kabusys 開発チーム

今後のリリースでは、strategy（戦略実装）、execution（注文実行）、monitoring（運用監視）の具体的実装や、テスト補強、ドキュメントの追加を予定しています。