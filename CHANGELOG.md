# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [0.1.0] - 2026-03-27
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ に主要サブパッケージを公開）。
- 環境・設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート探索は .git または pyproject.toml を起点に行い、カレントワーキングディレクトリに依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト向け）。
    - .env パーサは export プレフィックスやシングル/ダブルクォート、エスケープ、行末コメント等の一般的な形式に対応。
    - 上書き時に OS 環境変数を保護する protected キーセットの仕組みを実装。
  - Settings クラスを提供し、アプリケーションで利用する主要設定値（J-Quants / kabu / Slack / DB パス / ログ・環境判定等）をプロパティとして取得可能に。
    - 必須値は取得時に ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを設定（data/kabusys.duckdb, data/monitoring.db）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。is_live / is_paper / is_dev の判定プロパティを追加。
- ニュース NLP（AI）機能 (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON モードで送信してセンチメントを算出し、ai_scores テーブルへ保存する処理を実装。
  - 大量銘柄はチャンク（デフォルト 20 銘柄）で送信、1 銘柄あたり最大記事数・文字数でトリムする対策を導入。
  - API エラー（429、ネットワーク断、タイムアウト、5xx）に対してエクスポネンシャルバックオフで再試行し、最終的に失敗しても例外を送り出さずフェイルセーフ（スキップ）する設計。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検査、コード存在確認、数値検証、スコア ±1.0 クリップ）を実装。
  - スコア書き込みは部分失敗時に既存の他銘柄スコアを消さないよう、取得したコードのみ DELETE → INSERT で冪等に置換。
  - calc_news_window 関数を提供し、JST（前日 15:00 ～ 当日 08:30）に対応する UTC ナイーブ時間ウィンドウを返す。
- 市場レジーム判定（AI + 指標合成） (kabusys.ai.regime_detector)
  - ETF 1321（日経225 連動 ETF）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次でレジームを保存する処理を実装。
  - マクロ記事はキーワードフィルタ（日本および米国/グローバルのマクロ語句）で抽出し、LLM（gpt-4o-mini）で -1.0〜1.0 のスコアを取得。
  - API 呼び出し失敗時は macro_sentiment=0.0 で続行（フェイルセーフ）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の順で冪等性を確保。失敗時は ROLLBACK を試行。
  - ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を参照せず、target_date ベースで過去データのみを使用。
- リサーチ／ファクター計算 (kabusys.research)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を銘柄ごとに算出。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を算出。
    - calc_value: raw_financials から直近財務データを取得し PER（EPS=0/欠損時は None）・ROE を算出。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得する SQL ベース実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（浮動小数丸めで ties の漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - 研究用ユーティリティは標準ライブラリと DuckDB のみを前提として実装（pandas 等に依存しない）。
- データプラットフォーム (kabusys.data)
  - calendar_management モジュールを追加:
    - market_calendar を利用した営業日判定、翌/前営業日の検索、期間内営業日一覧取得、SQ 判定などのユーティリティ関数を実装。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を冪等更新する calendar_update_job を実装。バックフィル・健全性チェックを導入。
    - DB にカレンダーが未登録の場合は曜日ベースのフォールバックを採用。
  - pipeline / etl:
    - ETLResult データクラスを公開。ETL 実行結果（取得・保存件数、品質問題、エラー）を構造化して返却。
    - ETL 実装は差分更新、backfill、品質チェックフローを想定（jquants_client と quality モジュールと連携する設計）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

### 変更 (Changed)
- なし（初回リリースのため、変更履歴はありません）。

### 修正 (Fixed)
- なし（初回リリースのため、修正履歴はありません）。

### セキュリティ (Security)
- .env 読み込みで OS 環境変数を上書きしないデフォルト挙動と、上書き時に OS 環境変数を保護する protected キーセットを導入。これにより誤って既存の環境変数を上書きしてしまうリスクを低減。

### 既知の設計方針・注意点
- AI モジュール（news_nlp / regime_detector）は OpenAI API を利用します。API キーは引数経由または環境変数 OPENAI_API_KEY を指定してください。未設定の場合は ValueError を送出します。
- AI 呼び出しは JSON Mode（厳密な JSON 出力を期待）かつ堅牢なパース・バリデーションを行いますが、LLM の出力不整合はログに記録してスキップする方針です（サービス停止防止）。
- DuckDB をデータ層として利用し、テーブル存在チェックや日付変換等の互換性処理を行っています。
- ルックアヘッドバイアス対策として、日付参照はすべて呼び出し元から渡される target_date に基づいて行います。内部での date.today()/datetime.today() 参照は避けています。
- ai_scores / market_regime への書き込みは「該当日・該当コードのみ置換」することで部分失敗時のデータ保護を実現しています。

### マイグレーション / アップグレードノート
- 初回リリースのため特別な移行手順はありません。環境変数の設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY 等）と DuckDB/SQLite の配置を行ってください。

---

今後の予定（例）
- ai モデルやプロンプトの改良、より詳細な品質チェック、ETL 自動化ジョブの追加、モニタリング/アラート機能の実装を予定しています。