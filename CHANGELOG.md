# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
現在のパッケージバージョン: 0.1.0（初期リリース）

このファイルは与えられたコードベースから推測して作成しています。実装の意図や設計方針、外部依存や注意点を含めて記載しています。

## [Unreleased]

- 今後のリリースでの改善候補（推奨）
  - pipeline._get_max_date の実装確認（サンプルで断片的に終端している箇所があるため、実装完了の必要あり）
  - ドキュメント整備: 各モジュールの公開 API 使用例と必要な DB スキーマの明示
  - テスト・モックの例（OpenAI 呼び出し・J‑Quants クライアントなど）の追加
  - エラー監視・アラート設計（Slack通知連携等の統合テスト）

---

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）を追加し、data / strategy / execution / monitoring を公開モジュールとして宣言。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 設定管理
  - kabusys.config: 環境変数・.env ファイル読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml 基準）により、カレントワーキングディレクトリに依存しない自動 .env ロードを実装。
    - .env / .env.local の読み込み優先度を実装し、OS 環境変数を保護する protected 機構を搭載。
    - export KEY=val 形式やクォーテーション、インラインコメントなど現実的な .env フォーマットをパースするロジックを提供。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティ経由で取得（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境モード / ログレベル等）。
    - 必須環境変数未設定時は ValueError を送出する _require() を提供。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値の明示）。

- AI（自然言語処理）
  - kabusys.ai.news_nlp: ニュースセンチメント解析の実装（score_news）。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を行う calc_news_window を提供。
    - raw_news / news_symbols を集約して銘柄ごとの記事を作成し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを取得。
    - バッチサイズ・記事数・文字数上限などトークン肥大化を考慮した設計。
    - JSON Mode を用いたレスポンスバリデーションとスコアクリッピング（±1.0）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ、その他エラーはフェイルセーフでスキップ（処理継続）。
    - スコア書き込みは部分失敗に耐える idempotent な DELETE → INSERT ロジック（DuckDB executemany 空リスト回避の考慮あり）。
  - kabusys.ai.regime_detector: 市場レジーム判定（score_regime）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しは専用ラッパーを使用し、API リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - prices_daily / raw_news から必要データを取得し、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK 保護）。
    - ルックアヘッドバイアス防止（datetime.today() 等を参照せず、target_date 未満のデータのみ使用）。

- データプラットフォーム関連
  - kabusys.data.calendar_management: JPX カレンダー管理機能を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day など営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日が営業日）を行う設計。DB 登録値があればそれを優先。
    - calendar_update_job により J-Quants からの差分取得と再保存（バックフィル・健全性チェック含む）を実装。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開（etl の実行結果・品質問題・エラー情報を格納）。
    - ETL パイプライン設計（差分更新、保存、品質チェック）を反映したユーティリティを実装。J-Quants クライアント（jquants_client）と quality モジュールと連携する設計。
    - DataPlatform の運用を見据えたバックフィル、品質チェックの取り扱い方針を実装済み。
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター計算
  - kabusys.research パッケージ: ファクター計算・特徴量解析ユーティリティを公開（zscore_normalize を data.stats から利用）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER と ROE を算出（EPS が 0/欠損の場合は None）。
    - データ不足時の扱い（None 返却）と DuckDB SQL を活用した効率設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21）での将来リターン取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する関数を実装（コードで結合、欠損除外、最小サンプルチェック）。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。

- モジュール公開
  - kabusys.ai.__init__.py, kabusys.research.__init__.py で主要関数を再エクスポートし、公開 API を整理。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Security
- 環境変数の取り扱いに注意:
  - API キー（OpenAI 等）は Settings 経由または関数引数で受け取り、未設定時は明示的に ValueError を出すことで誤動作を防止。
  - .env 自動ロードでは OS 環境変数を protected として保護し、.env の意図しない上書きを避ける。

Notes / Requirements / 注意点
- 外部依存
  - OpenAI Python SDK（OpenAI.Client）を用いた実装を行っており、実行には OPENAI_API_KEY が必要（score_news, score_regime の引数から注入可）。
  - J-Quants 関連は kabusys.data.jquants_client モジュールに依存しており、実稼働時は該当クライアントの実装と API トークン等が必要。
  - DuckDB をデータストアとして想定（DuckDBPyConnection 型での引数）。
- 必要な DB スキーマ（主なテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など（各モジュールの SQL クエリ参照）。
- ルックアヘッドバイアス対策
  - AI スコアリングやファクター計算は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しないことでルックアヘッドを防止する設計が徹底されています。
- フェイルセーフ設計
  - LLM/API 呼び出し失敗時は例外を破壊的に伝播させず、スコアは 0.0 にフォールバックするか該当銘柄をスキップするなど、処理継続優先の設計。
- DuckDB の互換性対策
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）に配慮した分岐処理を実装。
- 実装上の注記（要確認）
  - 提供されたコードスニペットの末尾（pipeline._get_max_date 部分）が途中で切れているため、実際のリポジトリではその関数の実装確認・修正が必要な可能性があります。

---

発行者: kabusys 開発チーム（コードからの推測に基づく CHANGELOG）