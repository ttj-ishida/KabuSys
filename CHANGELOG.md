# CHANGELOG

このプロジェクトは Keep a Changelog に準拠して変更履歴を管理します。  
初期リリースの内容はコードベースから推測して記載しています。

## [Unreleased]

- （未リリースの変更なし）

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買プラットフォームのコア機能群を実装。

### 追加 (Added)

- 全体
  - パッケージ初期構成を追加。パッケージ名は `kabusys`、バージョン `0.1.0`。
  - モジュール公開インターフェースを `__all__` で定義（data, strategy, execution, monitoring）。
  - DuckDB を用いたローカル分析 / バッチ処理基盤を採用。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local を自動ロードする仕組みを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを抑制可能（テスト等向け）。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD に依存しない）。
  - `.env` のパース機能を堅牢化（export プレフィックス対応、クォート・エスケープ対応、コメント処理）。
  - 環境設定アクセス用の `Settings` クラスを提供。必須キー取得時はエラーを報告。
  - 既定値や検証を実装（KABUSYS_ENV の検証、LOG_LEVEL の検証、データベースパスの既定値など）。
  - 例: `from kabusys.config import settings` で各種設定プロパティにアクセス可能。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング: `news_nlp.score_news`
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく記事収集。
    - 銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) にバッチ送信し、JSON モードで結果をバリデーションして `ai_scores` テーブルへ書き込み。
    - バッチ処理（最大20銘柄 / チャンク）、記事トリム（最大文字数）、冗長な出力の復元ロジックなどを実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）は指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易化のため `_call_openai_api` を patch 可能に設計。
  - 市場レジーム判定: `regime_detector.score_regime`
    - ETF（コード 1321）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からデータを取得し、OpenAI（gpt-4o-mini）を呼び出して macro_sentiment を算出。
    - API の再試行・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 結果は冪等に `market_regime` テーブルへ保存（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易化のため `_call_openai_api` を独立実装（news_nlp と共有しないことでモジュール結合を低減）。

- データ処理 / ETL (src/kabusys/data)
  - ETL 結果データクラスを公開: `kabusys.data.ETLResult`（pipeline.ETLResult の再エクスポート）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分更新、IDempotent な保存（jquants_client の save_* を利用）、品質チェック（quality モジュール呼び出し）の枠組みを実装。
    - `ETLResult` により取得件数、保存件数、品質問題、エラーメッセージ等を集約して返却。
    - DuckDB を利用した最大日付取得ユーティリティ、テーブル存在チェック等を実装。
    - バックフィルオプション・カレンダー先読みなど ETL 運用上の考慮を組み込み。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants API から差分取得し保存）。
    - 営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録がまばらな場合の「曜日ベースフォールバック」を実装し、next/prev/get_trading_days と一貫した挙動を保証。
    - 最大探索日数を設定して（_MAX_SEARCH_DAYS）無限ループを防止。
    - バックフィルや健全性チェック（未来日付の異常検出）を実装。

- 研究（Research）機能 (src/kabusys/research)
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算する `calc_momentum`。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、平均売買代金、出来高比等を計算する `calc_volatility`。
    - Value: PER, ROE を計算する `calc_value`（raw_financials を参照）。
    - DuckDB での SQL ベース実装により、本番 API への影響なしにローカルで再現可能。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: `calc_forward_returns`（複数ホライズン対応、SQL 一括取得）。
    - IC（Information Coefficient）計算: `calc_ic`（Spearman ρ の実装、最低必要件数チェック）。
    - ランク変換ユーティリティ: `rank`（同順位は平均ランク、丸め処理で ties を安定化）。
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）。
  - 研究用ユーティリティをまとめて再エクスポート（zscore_normalize 等を含む）。

### 変更 (Changed)

- 設計面の重要な方針を明文化して実装
  - ルックアヘッドバイアス対策: 各モジュールで datetime.today()/date.today() を直接参照せず、target_date を外部から注入する設計。
  - LLM 呼び出しはフェイルセーフ化（API 失敗時にスコア 0.0 として継続）して、ETL / バッチ処理の頑健性を向上。
  - DuckDB の互換性考慮（executemany の空リスト回避など）を反映。

### 修正 (Fixed)

- 初版のため既知のバグ修正履歴はなし（将来のリリースで追加予定）。

### セキュリティ (Security)

- OpenAI API キーの取り扱い:
  - `news_nlp.score_news` / `regime_detector.score_regime` は API キーを引数で受け取り可能。引数が未指定の場合は環境変数 `OPENAI_API_KEY` を参照。
  - API キーが未設定の場合は明示的に ValueError を送出して失敗する設計（安全性のため）。

### 注意事項 / マイグレーションノート

- .env の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後や異なる配置での利用時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動管理を行ってください。
- DuckDB を使用する SQL 文は一部バージョン依存の振る舞い（例: リスト型バインドや executemany の空リスト）を考慮しています。DuckDB の古い/特殊バージョンを使う場合は互換性に注意してください。
- LLM 呼び出し周りはテスト容易性を考慮して `_call_openai_api` を patch できるように設計されています。ユニットテストではここを差し替えて外部 API 未依存で検証できます。
- ニュース収集ウィンドウや時刻計算は JST/UTC の換算を明確にしており、time zone の混入を避けるためすべて naive datetime（UTC 前提）で扱います。target_date を外部から渡す運用をしてください。

---

今後のリリースでは以下を予定（例示）:
- strategy / execution / monitoring モジュールの実装と注文実行パイプラインの統合
- モデル評価向けの可視化・バックテスト機能の追加
- 品質チェックの強化と自動アラート（Slack 連携等）
- Docker イメージや簡易デプロイ手順の追加

（この CHANGELOG はコードベースの実装内容を基に推定して作成しています。実際のコミット履歴と差異がある可能性があります。）