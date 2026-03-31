# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。  

- 変更ログの形式: https://keepachangelog.com/ja/1.0.0/
- 日付はリリース日を表します。

## [Unreleased]

開発中の変更はここに記載します。

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買 / データプラットフォーム向けに以下の主要機能を実装しています。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。公開バージョンは `0.1.0`。
  - パッケージの公開 API（__all__）として data, strategy, execution, monitoring を定義。

- 設定管理
  - kabusys.config.Settings を実装。環境変数から各種設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパス、監視閾値、実行環境など）を取得。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理、上書き制御、OS 環境変数の保護）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- AI（自然言語処理）機能
  - kabusys.ai.news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）を用いて銘柄ごとのニュースセンチメント（ai_score）を計算。
    - バッチ処理（最大20銘柄/リクエスト）、記事トリミング、JSON レスポンスのバリデーション、スコアのクリップ、DuckDB への冪等的書き込み（DELETE→INSERT）を実装。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで処理し、失敗時はフォールバックしてスキップ。テスト用に OpenAI 呼び出しを差し替え可能。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を日次で算出して market_regime テーブルへ書き込み。
    - マクロニュース取得ロジック、OpenAI 呼び出し、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを防ぐため、日付比較やウィンドウ選定を慎重に実装。

- データ基盤（Data）
  - kabusys.data.pipeline.ETLResult を公開。ETL 実行結果を構造化して返すデータクラスを提供。
  - kabusys.data.pipeline モジュール（ETL パイプラインの骨格）を実装。差分更新、バックフィル、品質チェック連携を想定した設計。
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理を実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルに存在するデータを優先し、未登録日は曜日ベース（週末判定）でフォールバックする一貫性のあるロジック。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（冪等）を行う。バックフィルと健全性チェックを備える。

- リサーチ（Research）
  - kabusys.research モジュール群を追加。以下のファクションを実装して公開:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と株価から PER / ROE を計算。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（複数ホライズン対応）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクにするランク付けユーティリティ。
  - zscore_normalize（kabusys.data.stats で提供）を再エクスポート。

### 変更 (Changed)
- n/a（初回リリースのため、過去からの変更はありません）。

### 修正 (Fixed)
- n/a（初回リリース）。

### 既知の制限／注意点 (Known issues / Notes)
- DuckDB スキーマ依存
  - 多くの関数は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, raw_financials, market_calendar, ai_scores, market_regime 等）に依存します。実行前にスキーマ準備が必要です。
- OpenAI API 依存
  - news_nlp と regime_detector は OpenAI API（gpt-4o-mini, JSON mode）を利用します。API キーは引数で注入可能（テスト時の差し替え容易）ですが、実運用では環境変数 OPENAI_API_KEY または api_key 引数が必要です。
- フェイルセーフ優先設計
  - LLM 呼び出しの失敗時は例外を上位へ投げず、フォールバック（スコア=0.0 もしくはスキップ）する挙動を多く採用しています。運用での失敗扱い方は呼び出し元で調整してください。
- .env 自動ロード
  - プロジェクトルート検出は .git または pyproject.toml に依存します。配布後や非典型構成では自動検出が失敗し、自動ロードがスキップされる場合があります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御してください。
- テストフック
  - OpenAI 呼び出しはモジュール内でラップされており、テスト時は該当プライベート関数を patch して差し替えることを想定しています。
- 部分的実装の可能性
  - ソースの一部（例: ETL モジュールの末尾など）が開発途中の断片的な状態である可能性があります。実行前に該当箇所のレビュー・補完を推奨します。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの拡充（自動売買ルール・発注ロジック・プロセス監視）。
- 品質チェックモジュールの強化と ETL の自動通知連携。
- モデル評価・バックテスト用のユーティリティ追加。

README やドキュメント（API 使用例、DB スキーマ、デプロイ手順）を追加していく予定です。