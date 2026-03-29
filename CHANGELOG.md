CHANGELOG
=========

すべての notable な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初期リリース。

### 追加 (Added)
- パッケージの初期バージョンを公開
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定モジュール (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）
  - export 付き行・クォート・エスケープ・インラインコメントなどを考慮した柔軟な .env パーサを実装
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）
  - override / protected 機構により OS 環境変数の保護を実現
  - Settings クラスを提供し、主要設定をプロパティで取得（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル）
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
    - タイムウィンドウ計算ユーティリティ calc_news_window を公開（JST を基準に前日 15:00 ～ 当日 08:30）
    - バッチサイズ制御、1銘柄あたり記事数/文字数のトリム処理、最大リトライ・指数バックオフを実装
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリッピング
    - DuckDB に対する冪等な書き込み（DELETE → INSERT）を実装し、部分失敗時に既存データを保護
    - テスト容易性のため _call_openai_api の差し替え（patch）を考慮

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースによる LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出
    - DuckDB の prices_daily/raw_news/market_regime を参照し、メトリクス計算 → OpenAI 呼び出し → 冪等な DB 書き込みまでを実装
    - LLM 呼び出しはフェイルセーフ（失敗時 macro_sentiment=0.0）およびリトライ/バックオフ対応
    - ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照せず、target_date 未満データなどで厳密に制約）

- データ処理・ETL（kabusys.data）
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 登録を優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック）
    - 最大探索日数などループ防止の安全策を備える

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETL 実行結果を格納する ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー集約）
    - 差分更新、backfill、品質チェック（quality モジュール連携）を想定した設計
    - jquants_client による保存処理の再利用（Idempotent 保存を前提）

  - jquants_client の想定連携（参照のみ）：fetch/save 系のクライアントを想定しているモジュール設計

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離などを計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と株価を組み合わせて PER, ROE を算出（EPS が 0/欠損時は None）
    - DuckDB SQL を活用し、営業日ベースの窓処理を実装

  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得（デフォルト: 1,5,21）
    - calc_ic: スピアマンランク相関（IC）を実装（ties 処理あり、3 銘柄未満は None）
    - rank: 同順位は平均ランク化（丸めで ties 検出の安定化）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー

- 共通設計方針・品質
  - DuckDB をメインの分析 DB として使用
  - ルックアヘッドバイアス防止のため、日付計算やクエリでの排他条件に注意した実装
  - OpenAI 呼び出しでの堅牢なエラー処理（429 / ネットワーク / タイムアウト / 5xx のリトライ）
  - DB 書き込みは冪等性を考慮（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
  - テスト容易性を配慮した差し替えポイント（_call_openai_api 等）

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 非推奨 (Deprecated)
- 初回リリースのため該当なし

### 削除 (Removed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- 初回リリースのため該当なし

注記
- この CHANGELOG はソースコードからの推定に基づく初期リリースの説明です。実際の API キーや外部サービス（OpenAI / J-Quants / kabu ステーション）との接続設定は環境変数で行ってください（Settings クラス参照）。
- OpenAI SDK、duckdb 等の外部依存があります。README / pyproject.toml に依存関係を明記することを推奨します。