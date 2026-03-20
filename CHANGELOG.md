# Changelog

すべての変更は Keep a Changelog の慣例に従っています。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]

（現在のリポジトリ状態は v0.1.0 として最初の公開リリースが作成されています。今後の変更はここに記載してください。）

---

## [0.1.0] - 2026-03-20

初回公開リリース — KabuSys: 日本株自動売買システムの基盤実装

### 追加 (Added)
- パッケージ構成
  - 基本パッケージ `kabusys` とサブパッケージ `data`, `strategy`, `execution`, `research`, `monitoring` を導入。
  - バージョン: `0.1.0`（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数・.env ファイル読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
    - .env パーサは export フォーマット、クォート・エスケープ、インラインコメントなどに対応。
    - 必須変数取得時の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の値チェック）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制限対応（120 req/min）。
    - 再試行（指数バックオフ、最大3回）および特定ステータス（408/429/5xx）でのリトライ対応。
    - 401 Unauthorized の際の自動トークンリフレッシュ（1 回）を実装。
    - ページネーション対応でデータを全件取得。
    - DuckDB への保存関数（raw_prices / raw_financials / market_calendar）を実装し、ON CONFLICT による冪等性を確保。
    - データ型変換ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集
  - RSS フィード収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（Yahoo Finance）を設定。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント削除）。
    - 受信バイト数上限（10MB）などメモリ DoS 対策。
    - XML パースに defusedxml を使用して XML Bomb 等の攻撃を軽減。
    - 挿入は冪等化（ON CONFLICT / DO NOTHING 想定）を前提とした設計。
    - 記事 ID を正規化 URL の SHA-256 等で生成する方針を記載（冪等性確保）。

- リサーチ（ファクター計算・解析）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対 ATR、出来高比率、平均売買代金）、Value（PER、ROE）を計算。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する実装。
    - 欠損やデータ不足に対する安全な扱い（必要行数未満で None を返す等）。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman ランク相関）計算ユーティリティ、ランク関数、ファクター統計サマリーを実装。
    - pandas 等の外部ライブラリに依存しない純 Python 実装。

- 特徴量エンジニアリング
  - build_features を実装（src/kabusys/strategy/feature_engineering.py）。
    - research の生ファクターを取得してユニバースフィルタ（株価 >= 300円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize の利用）および ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位での置換（DELETE→INSERT をトランザクションで実施）により冪等性を確保。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成
  - generate_signals を実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を実装。外部から重みを渡した場合は検証・正規化。
    - final_score を算出し、閾値（デフォルト 0.60）超で BUY シグナル生成。Bear レジーム判定時は BUY 抑制。
    - エグジット（SELL）判定ロジックを実装（ストップロス -8%、final_score の閾値未満）。
    - features / ai_scores / positions / signals テーブルを参照し、signals テーブルへ日付単位で置換（冪等）。
    - AI スコア未登録時は中立値で補完する実装（欠損保護）。
    - 重みの不正値（NaN/Inf/負値/非数値）は警告してスキップ。

- ロギング・検査
  - 各主要処理に logger 呼び出しを追加（info/debug/warning レベル）で運用時のトレースを容易に。

### 変更 (Changed)
- N/A（初回リリースのため履歴に特定の「変更」はありません）。

### 修正 (Fixed)
- N/A（初回リリースのため履歴に特定の「修正」はありません）。

### セキュリティ (Security)
- ニュース XML パースに defusedxml を使用し、XML 関連攻撃を軽減。
- RSS URL 正規化・スキーム検査等により SSRF や不正 URL を抑制する方針を明示。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（コード内コメント参照）:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の実際の DB INSERT/ON CONFLICT 実装や記事 ID 生成は設計方針として記載されているが、環境に応じた追加実装やテストが必要。
- DuckDB テーブル定義（スキーマ）や外部コンポーネント（Slack 通知、execution 層など）の統合は別途実装/設定が必要。
- J-Quants API クライアントはネットワーク・API 依存のため、運用時は適切なトークン管理とレート管理に注意が必要。

---

開発・運用に関する問い合わせやバグ報告は Issue を立ててください。