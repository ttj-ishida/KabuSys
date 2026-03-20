# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。本リポジトリは日本株自動売買システム（KabuSys）のコアライブラリ群を提供します。
主要な追加点・設計方針は以下の通りです。

### Added
- パッケージ基礎
  - パッケージエントリ（src/kabusys/__init__.py）を追加し、バージョンを "0.1.0" に設定。
  - 公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサ（クォート処理・エスケープ・inline コメントの考慮、export プレフィックス対応）を提供。
  - .env のロード優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス /システム（env / log_level）等の設定プロパティを提供。必要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）に対して未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を限定）。

- データ収集（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（ページネーション、レート制限、リトライ、401 自動リフレッシュなど）。
  - 固定間隔スロットリングを行う RateLimiter 実装（120 req/min を想定）。
  - 再試行戦略（指数バックオフ、最大 3 回。HTTP 408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - get_id_token によるリフレッシュトークン→IDトークン取得、内部キャッシュを保持してページネーション間で再利用。
  - API レスポンス（株価日足 / 財務 / マーケットカレンダー）を取得する fetch_* 系関数を実装。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT/DO UPDATE を使用）。
  - レスポンス値の安全な数値変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集処理を実装（既定ソースに Yahoo Finance を登録）。
  - XML の安全パースに defusedxml を利用して XML Bomb 等に対処。
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）を実装し、記事 ID を正規化後の SHA-256（先頭32文字）等で生成して冪等性を保持。
  - 受信最大 byte 制限（10MB）や SSRF を意識した URL 検査の設計、バルク INSERT のチャンク化、INSERT RETURNING を用いた挿入件数の正確な把握などの実装方針を導入。

- リサーチ（src/kabusys/research/*.py）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - 期間用の定数（21/63/126/200/20 日等）やスキャンバッファの取扱いを実装。
  - feature_exploration:
    - calc_forward_returns（将来リターンの計算、複数ホライズン対応、入力検証あり）。
    - calc_ic（Spearman のランク相関を計算、サンプル不足時は None を返す）。
    - factor_summary（カウント・平均・分散・std・min/max/median を算出）。
    - rank（同順位は平均ランクとするランク付け実装、丸めで ties 検出の安定化）。
  - research パッケージの __all__ に主要機能を公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装。research の calc_* 関数で得た raw factors をマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定列に対して Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへ日付単位の置換（DELETE→INSERT をトランザクションで行い原子性を保証）。処理は冪等。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装。features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を算出。
  - デフォルト重み・閾値を実装し、ユーザ指定 weights は検証（未知キーや不正値を除外）して正規化（合計 1 にスケーリング）。
  - AI レジームスコアに基づく Bear 判定（サンプル閾値あり）を実装し、Bear 時は BUY を抑制。
  - BUY シグナルは閾値超え銘柄に対してランク付け、SELL はポジション（positions テーブル）に対するストップロス（終値 / avg_price - 1 <= -8%）とスコア低下（final_score < threshold）で判定。
  - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへの日付単位置換をトランザクションで実施。
  - 未実装のエグジット条件（トレーリングストップ、時間決済）はコード内に注記。

- Strategy パッケージエクスポート（src/kabusys/strategy/__init__.py）
  - build_features, generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- ニュース XML のパースに defusedxml を使用し XML-related 攻撃を緩和。
- news_collector で HTTP URL 検査や受信バイト数上限を設け、SSR F/メモリ DoS のリスク低減を考慮。
- J-Quants クライアントのトークン処理とリフレッシュに注意を払い、401 処理は限定的に自動リフレッシュ（無限再帰防止）を行う実装。

### Notes / Known limitations
- generate_signals の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等が必要となる旨の注記あり。
- 一部ユーティリティ（zscore_normalize など）は data パッケージ内に実装されている想定（今回の差分には定義を含まず参照している）。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, market_calendar, raw_news 等）は想定されており、マイグレーション/スキーマ作成は別途必要。
- 外部ライブラリへの依存を最小化する設計（pandas 等非依存）を採用。ただし defusedxml は利用。

---

今後の予定（例）
- トレーリングストップ・時間決済のエグジット条件実装
- 追加の監視・モニタリング（monitoring パッケージ）の実装
- テストカバレッジ拡充と CI 用のワークフロー整備

（必要であれば、各ファイルの変更点をより細かく分割して追記できます）