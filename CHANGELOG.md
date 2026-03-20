# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを追加しました。下記はコードベースから推測される主な追加・設計方針・注意点のまとめです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、主要サブパッケージの公開（data, strategy, execution, monitoring）を定義。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサーはコメント行・export プレフィックス・シングル・ダブルクォート・エスケープを考慮した堅牢な実装。
    - .env 読み込み時の上書きルール（OS 環境変数を保護する protected set）をサポート。
    - 必須設定取得のヘルパー `_require`、および Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、実行環境/ログレベル判定などのプロパティを備える）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API へアクセスするクライアントを実装。ページネーション対応の fetch_* 関数を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限を守る固定間隔スロットリング（_RateLimiter, 120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）とステータスコードによる再試行ポリシー（408/429/5xx を対象）。429 の場合は Retry-After を尊重。
    - 401 発生時はトークンを自動リフレッシュして再試行する仕組み（トークンキャッシュと get_id_token を利用、無限再帰防止）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT（UPSERT）を利用し重複を排除。
    - データ変換ユーティリティ `_to_float` / `_to_int` を実装し、不正な数値・空値を安全に扱う。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を収集し raw_news テーブルに保存する方針を実装（記事ID は正規化 URL の SHA-256 先頭を用いるなどで冪等性を確保）。
    - XML パースに defusedxml を使用（XML Bomb 等の防御）。
    - 受信最大バイト数制限、トラッキングパラメータ除去、URL 正規化、SSRF 対策（HTTP/HTTPS のみ許可想定）など堅牢性を考慮。
    - バルク INSERT のチャンク処理や、INSERT RETURNING を利用して実際に挿入された件数を正確に把握する設計。

- リサーチ（ファクター計算・解析）
  - src/kabusys/research/factor_research.py:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（per, roe）等、StrategyModel に基づくファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB のウィンドウ関数を利用した効率的な SQL 実装、データ不足時の None ハンドリング、休日・欠損を考慮したスキャン範囲のバッファ設計などを採用。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関に基づく IC を実装。サンプル不足や ties の取り扱いに配慮。
    - factor_summary, rank: ファクターの基本統計量やランク付けユーティリティを提供。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

  - src/kabusys/research/__init__.py:
    - 上記リサーチ機能を再公開。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールが計算した生ファクターを統合・正規化し、features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価・20日平均売買代金）を適用。
    - 数値ファクターを Z スコアで正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - トランザクションで日付単位の置換（DELETE + INSERT のトランザクション）を行い冪等性・原子性を確保。
    - ルックアヘッドバイアス回避の設計を明記（target_date 時点のデータのみ使用）。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合し final_score を計算して BUY/SELL シグナルを生成する generate_signals を実装。
    - momentum/value/volatility/liquidity/news といったコンポーネントスコアを計算するユーティリティを提供（シグモイド変換、欠損時は中立値 0.5 で補完）。
    - 重み（weights）の入力を許容し、デフォルト値からフォールバック・検証・再スケーリングを行うロジックを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、ただし十分なサンプルがあるときのみ）を実装し、Bear 時は BUY を抑制。
    - エグジット判定（ストップロス、スコア低下）を実装。positions / prices_daily を参照して SELL シグナルを生成。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。

- Strategy API 再公開
  - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。

### Changed
- （初版のため該当なし）内部設計や命名規約は StrategyModel.md / DataPlatform.md の設計指針に準拠している旨の注釈が多数追加されている。

### Fixed
- （初版のため該当なし）コード内にログ出力や入力検証を多く追加し、欠損や異常ケースでの安全な動作を考慮。

### Security
- 認証トークンの扱い
  - J-Quants トークンは設定（環境変数）から取得する仕組み。401 発生時は自動リフレッシュを行い再試行する実装。ただし設定が未提供の場合に例外を投げる。
- XML/HTTP の安全対策
  - ニュース収集で defusedxml を使用し、XML ベースの攻撃を軽減。
  - URL 正規化とトラッキングパラメータ除去、受信サイズ制限、HTTP/HTTPS スキームの想定などで SSRF・DoS 対策を考慮。

### Known Issues / Notes
- execution と monitoring パッケージは初期公開のみ（src/kabusys/execution/__init__.py は空）で、発注 API との統合実装は本リリースでは含まれていない（戦略層は発注層に依存しない設計）。
- 一部の戦略ロジック（例: トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price, entry_date 等）が必要で未実装として言及されている。
- DuckDB のテーブルスキーマや外部環境（.env の整備、DB ファイルパス、Slack トークン等）は利用者側で準備が必要。
- ニュース記事の記事ID生成や URL 正規化は設計に基づいているが、実運用でのソース多様化やエンコーディングの特殊ケース等の追加処理は今後必要になる可能性がある。

---

メジャー変更やバグ修正が発生した場合は、この CHANGELOG に追記してください。