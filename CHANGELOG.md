# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
次回リリースまでの変更は Unreleased に記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-21
初期リリース。日本株自動売買システムのコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロードの挙動:
    - プロジェクトルートを .git / pyproject.toml から探索して .env / .env.local を読み込む（CWD に依存しない実装）。
    - OS 環境変数を保護する protected 機能、.env.local は .env を上書きする挙動。
    - 環境変数の自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理を考慮。
  - 必須設定取得時の検証（未設定時は ValueError）。KABUSYS_ENV / LOG_LEVEL の許容値検証。
  - 主要設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）、DBパス（DuckDB/SQLite）を提供。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔のスロットリングによるレート制限管理（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）および HTTP ステータスに応じたリトライ戦略（408, 429, 5xx 等）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有機構。
    - ページネーション対応でのデータ取得ループ。
  - 取得関数:
    - fetch_daily_quotes（株価日足 / ページネーション対応）
    - fetch_financial_statements（財務データ / ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
  - JSON デコードエラーやネットワーク例外時の適切なエラーハンドリング。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news に保存する基本実装。
  - セキュリティ・堅牢性対策を導入:
    - defusedxml を利用して XML Bomb 等を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設定してメモリ DoS を抑制。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、パラメータソート）を実装。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保する方針（ドキュメントに記載）。
  - データベースへのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）して実行。
- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率の計算。
    - calc_value: PER（price / EPS）、ROE の算出（raw_financials と prices_daily を組合せ）。
    - DuckDB を使用した SQL + Python 実装で、外部ライブラリに依存しない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括取得（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時の None 戻りを考慮。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク関数（丸めで ties の判定漏れを防止）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research 側の生ファクター（calc_momentum / calc_volatility / calc_value）を取得してマージ。
    - ユニバースフィルタ（最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8 円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を確保（トランザクション）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントスコア変換にシグモイド関数を利用し、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を採用。ユーザ重みは検証・フィルタリング後に正規化して合計が 1.0 になるよう再スケール。
    - BUY 閾値デフォルト _DEFAULT_THRESHOLD = 0.60、Stop-loss _STOP_LOSS_RATE = -0.08。
    - Bear レジーム（ai_scores の regime_score 平均が負）検知時は BUY シグナルを抑制。
    - 保有ポジションに対するエグジット判定（ストップロス、スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへの日付単位置換（DELETE + bulk INSERT）で冪等性と原子性を保証。
- その他ユーティリティ
  - データ変換ヘルパー（_to_float / _to_int）やトークンキャッシュ、RateLimiter などの内部ユーティリティを追加。
  - ロギングを各モジュールで適切に出力（info/warning/debug）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- RSS 解析に defusedxml を使用して XML 関連の攻撃を軽減。
- ニュース収集で受信サイズ制限を導入し、メモリ DoS を防止。
- ニュース URL 正規化でトラッキングパラメータを除去し、記事識別子の安定化を図る。
- J-Quants クライアントでのトークン自動刷新は無限再帰を起こさないよう allow_refresh フラグで制御。

### 既知の制限 / TODO
- signal_generator のトレーリングストップや時間決済など一部のエグジット条件は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- news_collector の一部の SSRF 防止ロジック（IP 判定・ソケットチェック等）は実装の一部が別箇所に分かれる可能性あり（モジュール内で意図が記載されている）。
- PBR・配当利回りなどのバリューファクターは現バージョンでは未実装。
- 外部依存（pandas 等）を使わない設計のため、処理効率や利便性の点で将来的に検討の余地あり。

---

メジャー/マイナー/パッチに関する方針は SemVer に準拠します。今後の改善やバグ修正は Unreleased に積み上げて次バージョンで反映します。