# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" のガイドラインに従い、変更はセマンティックバージョニングに基づいて管理します。

※ 以下はリポジトリ内のソースコードから推測して作成した初期リリースの変更履歴です（実装方針や設計ノートを含む）。

## [Unreleased]

- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システムのコアライブラリを公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__`（__version__ = "0.1.0"、サブパッケージ公開）
- 設定・環境変数管理
  - `kabusys.config`
    - .env 自動ロード機能（プロジェクトルート検出：.git / pyproject.toml を探索）
    - .env / .env.local の読み込み順序および上書き保護（OS 環境変数保護）
    - 複雑な .env の行解析（export プレフィックス、クォート、インラインコメント、エスケープ処理）
    - 設定取得用 `Settings` クラス（J-Quants / kabu API / Slack / DB パス / 環境判定等）
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - 値検証（KABUSYS_ENV, LOG_LEVEL）とヘルパープロパティ（is_live, is_paper, is_dev）
- AI（自然言語処理）モジュール
  - `kabusys.ai.news_nlp`
    - ニュース記事の銘柄単位センチメントスコア算出（OpenAI gpt-4o-mini の JSON Mode を利用）
    - タイムウィンドウ計算（JST ベース → UTC 比較に対応）
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数トリミング、レスポンス検証、スコアクリップ（±1.0）
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）
    - DuckDB への冪等的書き込み（対象コードのみ DELETE → INSERT）
    - テスト用フック（内部の OpenAI 呼び出し関数をパッチ可能）
  - `kabusys.ai.regime_detector`
    - 市場レジーム判定機能（ETF 1321 の 200 日移動平均乖離 + マクロニュース LLM センチメントの重み合成）
    - LLM によるマクロセンチメント評価（gpt-4o-mini, JSON 出力期待）
    - スコア合成ロジック（MA 重み 70%、マクロ重み 30%、クリップと閾値判定で bull/neutral/bear を決定）
    - 冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - フェイルセーフ：API 失敗時は macro_sentiment = 0.0
- Data（データ管理）モジュール
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - market_calendar テーブル優先、未登録日は曜日ベースのフォールバック
    - カレンダーバッチ更新ジョブ（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）
    - 最大探索範囲設定や不整合検出ロジック
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプライン基盤、差分取得・保存・品質チェックの設計
    - `ETLResult` データクラス（実行結果、品質問題、エラー収集、シリアライズ用 to_dict）
    - DuckDB テーブル存在チェック・最大日付取得のユーティリティ
    - 市場カレンダー調整ヘルパー（非営業日を最近の営業日に調整するロジック）
  - `kabusys.data.__init__` に ETL 結果の公開インターフェースを準備
- Research（リサーチ）モジュール
  - `kabusys.research.factor_research`
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）計算
    - DuckDB を用いた SQL ベース計算（prices_daily / raw_financials のみ参照）
    - 欠損やデータ不足時の None 返却、結果は (date, code) ベースの dict リスト
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（任意ホライズン、取り扱い上限 252 営業日）
    - IC（Information Coefficient：Spearman ρ）計算
    - ランク変換ユーティリティ（同順位は平均ランク、丸めで ties を安定化）
    - ファクター統計サマリー（count/mean/std/min/max/median）
  - `kabusys.research.__init__` で主要関数を再エクスポート
- ロギング
  - 各モジュールで詳細な logger 呼び出しを実装（処理状況・警告・例外ログ）

### 変更 (Changed)
- （初期リリースのため変更履歴なし）

### 修正 (Fixed)
- （初期リリースのため修正履歴なし）

### 注意点 / 設計上の決定 (Notes)
- ルックアヘッドバイアス防止のため、date / target_date ベースでの計算を徹底（datetime.today()/date.today() を直接参照しない設計）。
- OpenAI API 呼び出しについてはフェイルセーフ設計：
  - LLM の呼び出し失敗時はスコアを 0.0 にフォールバックし処理を継続（例外を上位に投げない箇所あり）。
  - 再試行ロジック（指数バックオフ）を実装。
  - テスト容易性のために内部 API 呼び出し関数をパッチ可能に設計。
- DuckDB 互換性に配慮：
  - executemany に空リストを与えないガード（DuckDB 0.10 の制約への対応）。
  - SQL 生成時に互換性を意識した実装（ROW_NUMBER / ウィンドウ関数等）。
- DB 書き込みはなるべく冪等（DELETE→INSERT、ON CONFLICT、トランザクション制御）を意識。
- .env 自動ロードは便利だが副作用もあるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。

### 既知の制約 / 必要な環境変数
- OpenAI API キー: `OPENAI_API_KEY`（関数引数での注入も可能）
- J-Quants / kabu / Slack 関連の必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等）は `Settings` 経由で要求され、未設定時は ValueError を送出する箇所があるため注意。
- デフォルトの DB パスは `data/kabusys.duckdb`（DuckDB）および `data/monitoring.db`（SQLite）に設定されているが、環境変数で上書き可能。

---

今後の予定（例）
- ai モジュールの追加評価（モデル切替やパフォーマンス改良）
- ETL の並列化や品質チェックルールの追加
- モデルの学習 / バックテスト用ユーティリティの追加

もし CHANGELOG に追記してほしい具体的な変更点（実際のコミットやリリース日、追加で強調したい設計判断など）があれば教えてください。追記・修正して再生成します。