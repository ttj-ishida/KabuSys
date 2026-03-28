# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  
安定リリースのバージョニングには SemVer を使用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - 上書きルール: OS 環境変数を保護する protected 機構、.env と .env.local の優先度制御
  - Settings クラスを提供（環境変数からの設定取得ラッパー）
    - J-Quants / kabu ステーション / Slack / DB パスなどのプロパティ
    - KABUSYS_ENV と LOG_LEVEL 値検証（許容値チェック）
    - duckdb_path / sqlite_path の Path 型返却

- データ関連 (kabusys.data)
  - ETL パイプラインの骨組み（kabusys.data.pipeline）
    - ETLResult データクラス（実行結果の集約、品質問題やエラーメッセージの格納）
    - 差分取得・バックフィル・品質チェックを想定した設計
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル連携）
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 夜間バッチ更新ジョブ: calendar_update_job（J-Quants からの差分取得と冪等保存）
    - DB データがない場合は曜日ベースのフォールバック（週末は非営業日扱い）
    - 最大探索日数・バックフィル等の安全ガード実装

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算群を実装
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials と prices_daily を組合せ）
  - 特徴量探索ユーティリティ
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ
  - 設計方針として DuckDB 接続を受け取り SQL + Python で完結する形を採用（外部 API 呼び出しや pandas 非依存）

- AI / ニュースセンチメント (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols を用い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信
    - JSON Mode を利用したレスポンス検証・パース
    - バッチ処理・チャンク（最大20銘柄）化、1銘柄あたりの記事/文字上限設定（記事数/文字数でトリム）
    - リトライ戦略: 429・ネットワーク・タイムアウト・5xx に対する指数バックオフ
    - レスポンス検証で不正な結果は無視し、スコアを ±1.0 にクリップ
    - ai_scores テーブルへ冪等的に（対象コードのみ DELETE → INSERT）書き込み
    - フェイルセーフ: API 失敗時は処理をスキップして継続（例外は上位へ伝搬させず、呼び出し側は結果数で失敗を検知可能）
    - calc_news_window: タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）
    - score_news(conn, target_date, api_key=None) 公開 API（戻り値: 書き込んだ銘柄数）
  - regime_detector モジュール
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次市場レジーム判定
    - マクロニュースは news_nlp のウィンドウ計算を再利用して抽出
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）
    - マクロスコアリングは記事がない場合 0.0、API 失敗時は 0.0 にフォールバック（警告をログ）
    - レジームスコアを [-1, 1] にクリップし閾値でラベル付け（bull/neutral/bear）
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - score_regime(conn, target_date, api_key=None) 公開 API（戻り値: 成功時 1、API キー未設定は ValueError）

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- OpenAI API キーの取り扱い
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して誤使用を防止
- .env 自動ロードで OS の既存環境変数を保護する protected 機構を導入

### 実装上の注意 / 設計上の決定
- ルックアヘッドバイアス回避
  - 日付処理で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）
  - DB クエリで date < target_date 等の排他条件を採用
- DuckDB の互換性考慮
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約への対応）
  - リストバインドの互換性問題を避けるため個別 DELETE を行う実装
- 冪等性
  - ETL / calendar / ai スコア保存処理は基本的に既存データを上書きせず、対象のみ削除して挿入することで部分失敗時に既存データを保護
- ロギングおよびエラーハンドリング
  - 外部 API 呼び出しはリトライ＋ログ、致命的でない失敗はフェイルセーフとして 0 や空結果へフォールバック

### 既知の制限
- PBR・配当利回りなど一部バリューメトリクスは未実装（calc_value の Note に記載）
- news_nlp と regime_detector の OpenAI 呼び出しは gpt-4o-mini を想定（将来的にモデル切替が可能）
- calendar_update_job は J-Quants クライアント実装（kabusys.data.jquants_client）に依存するため、API の可用性に左右される

---

今後の予定（例）
- strategy / execution / monitoring 部分の具象実装（発注ロジック、モニタリング通知）
- テストカバレッジ拡張と CI 設定
- API 呼び出しのメトリクス収集とリトライ/レート制限の改善

(注) 本 CHANGELOG はリポジトリ内のソースコードから機能・設計意図を推測して作成しています。実際のリリースノートとして用いる場合は、差分やコミット履歴に基づく検証を推奨します。