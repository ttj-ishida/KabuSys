# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
日付はリリース日を示します。

## [Unreleased]

---

## [0.1.0] - 2026-04-01

初期リリース。本バージョンで実装された主要機能と設計上の注意点をまとめます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ により整理（data, strategy, execution, monitoring 等を想定）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定ロード機能を実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にルートを探索して .env/.env.local を自動読込。
  - .env 解析器: コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - 読み込み優先順位: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu ステーション設定、Slack、DBパス、監視閾値、環境モード/ログレベル判定など）をプロパティ経由で取得可能。
  - 必須キー未設定時に明瞭な ValueError を投げる _require 実装。
  - 環境変数保護（protected set）を考慮した上書き制御。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信して銘柄別センチメント ai_score を ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ算出（JST 基準: 前日 15:00 〜 当日 08:30 を UTC に変換する calc_news_window）。
    - 1銘柄あたりの記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチサイズ（最大銘柄数）でチャンク化して API コール（_BATCH_SIZE）。
    - レスポンスの厳格なバリデーションと JSON 復元ロジック（余分な前後テキストが混入した場合の最外側 {} 抽出）。
    - スコアを ±1.0 にクリップし、有効スコアのみ DB に置換（部分失敗時は他銘柄の既存スコアを保護）。
    - API 呼び出し失敗（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフとリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し関数はモジュール内で差し替え可能（_call_openai_api の patch 想定）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news からデータを取得。ma200 乖離は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロ記事抽出はマクロキーワード群に基づくフィルタ。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）へのリトライ、エラー種別による扱い（5xx はリトライ、非5xx はフォールバック）を実装。
    - 合成スコアを -1.0〜1.0 にクリップし閾値でラベリング（BULL/BEAR/NEUTRAL）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
    - テスト容易性のため _call_openai_api を差し替え可能。

- データ処理（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの差分取得・保存ロジック（calendar_update_job）を実装。J-Quants クライアント経由で取得し idempotent に保存。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末は非営業日）。最大探索日数で無限ループ防止。
    - バックフィル・健全性チェックを実装（直近 _BACKFILL_DAYS の再フェッチ、未来日付の異常検出によるスキップ）。

  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（etl.ETLResult を再エクスポート）。
    - 差分更新、保存、品質チェック（quality モジュール）を想定した設計。
    - 最終取得日の差分計算、バックフィル、エラー収集を行う設計方針をコード上に反映。
    - DuckDB を用いることを前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日以上データがない場合は None）。
    - calc_volatility: ATR(20), 相対 ATR, 20日平均売買代金, 出来高比率 等を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。
    - DuckDB のウィンドウ関数を用いた実装で、外部 API へアクセスしない安全設計。
  - 特徴量解析（feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得可能（horizons の検証あり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（有効レコード数が不足する場合は None）。
    - rank: 同順位は平均ランクで処理する安定実装。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - zscore_normalize 等のデータ統計ユーティリティを再エクスポート。

### 変更 (Changed)
- 初版のため過去バージョンからの変更はありません（初回公開）。

### 修正 (Fixed)
- 初期リリースに含まれる設計上の堅牢化・フェイルセーフ処理:
  - OpenAI API 呼び出しでの JSON パース失敗や API エラーをスキップして処理継続するフォールバックを多所に採用。
  - DuckDB の executemany に空リストを渡せない点を考慮したガード実装（空チェック）。
  - market_regime / ai_scores など DB 書き込み処理でのトランザクションとロールバックを明示。

### 注意点 / 設計上の制約
- 全モジュールでルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計を採用。関数の引数として target_date を明示的に渡す必要がある。
- OpenAI API 利用部分は API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
- news_nlp / regime_detector は gpt-4o-mini の JSON Mode を前提とした実装であり、API レスポンスのフォーマット依存がある（バリデーションと復元処理を実装済み）。
- DuckDB を前提とした SQL 実行（ROW_NUMBER, WINDOW 関数等）を利用。互換性のある DuckDB バージョンでの実行を想定。
- テストしやすさのため、OpenAI 呼び出しポイントはモック可能（_call_openai_api を patch）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

将来的なリリースでは以下を予定しています（案）:
- strategy / execution / monitoring の実装拡充（発注ロジック・監視/アラートの実装）。
- ai モデルやプロンプト改善、API 呼び出しのメトリクス/監視追加。
- ETL の並列化や差分計算の最適化、品質チェック強化。