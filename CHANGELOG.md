# Keep a Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従います。

※この CHANGELOG はコードベースから実装内容を推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0）を追加。
  - 公開 API: kabusys.data / kabusys.research / kabusys.strategy / kabusys.execution（パッケージ構成）。

- 設定管理（kabusys.config）
  - .env ファイル（.env/.env.local）および環境変数からの設定自動読み込みを実装。
  - プロジェクトルート探索ロジックを追加（.git または pyproject.toml を基準）。
  - .env パーサ実装:
    - export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応。
    - コメント判定ロジック（クォート有無で異なる扱い）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境設定 等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値制約）。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
    - 固定間隔の RateLimiter（120 req/min）によるスロットリング。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 時のリフレッシュ処理（リフレッシュトークンからの idToken 取得、1 回まで自動リトライ）。
    - ページネーション対応とモジュールレベルのトークンキャッシュ。
    - JSON デコードエラーハンドリング。
  - データ保存関数（DuckDB への冪等保存）:
    - save_daily_quotes: raw_prices への保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials への保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）。
    - 入力変換ユーティリティ: _to_float / _to_int（堅牢な型変換）。
  - データ取得関数:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュール（デフォルトに Yahoo Finance のビジネス RSS を設定）。
  - セキュアな XML パーシング（defusedxml を使用）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリ整列、フラグメント除去）。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）や SSRF 対策を考慮した設計。
  - バルク INSERT チャンク処理により DB オーバーヘッド軽減。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、および 200 日移動平均乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - calc_value: per / roe を raw_financials と prices_daily から計算。
    - DuckDB のウィンドウ関数を活用した効率的な実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）計算（tie を平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties 判定の安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で算出した生ファクターを正規化・合成して features テーブルへ書き込み。
  - ユニバースフィルタ:
    - 株価 >= 300 円（_MIN_PRICE）。
    - 20 日平均売買代金 >= 5 億円（_MIN_TURNOVER）。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップ。
  - features テーブルへの日付単位 UPSERT（削除→挿入で原子性を確保）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成。
  - スコア計算コンポーネント:
    - momentum / value / volatility / liquidity / news の重み付け（デフォルト w: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10）。
    - デフォルト BUY 閾値: 0.60。
    - スコア変換にシグモイド、欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定:
    - ai_scores の regime_score 平均が負の場合を Bear と判定（サンプル閾値あり）。
    - Bear レジーム時は BUY シグナルを抑制。
  - エグジット判定（SELL ロジック）:
    - ストップロス（終値/avg_price - 1 < -8%）を優先。
    - final_score が threshold 未満で SELL。
    - 保有ポジション情報がない/価格欠損時の安全措置（処理をスキップまたはデフォルト降格）。
  - signals テーブルへの日付単位置換（削除→挿入）で冪等性を確保。
  - ユーザー指定の weights 検証・正規化機構を実装（無効値は警告して無視、合計が 1 でない場合はリスケール）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- news_collector で defusedxml を使用し XML 攻撃を軽減。
- RSS 受信サイズ制限や URL 正規化により SSRF / DoS のリスク低減を設計に組み込み。
- J-Quants クライアントでトークンリフレッシュを安全に扱い、無限再帰を防止（allow_refresh フラグ）。

### Performance
- DuckDB のウィンドウ関数と単一クエリ集計を活用してファクター計算・将来リターン算出のパフォーマンスを意識した実装。
- news_collector のバルク INSERT チャンク処理により DB オーバーヘッドを低減。
- API レート制御（固定間隔）でレート制限に適合。

### Notes / Known limitations
- 一部のエグジット条件は未実装（コード内注釈）:
  - トレーリングストップ（peak_price を positions テーブルに保持する必要あり）。
  - 時間決済（保有 60 営業日超過）等。
- 多くの関数は DuckDB の特定スキーマ（raw_prices, prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提としているため、事前にスキーマ作成が必要。
- news_collector での外部依存は defusedxml のみ。pandas 等を使わず標準ライブラリ中心で実装。
- 環境変数読み込み:
  - 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。
  - OS 環境変数は .env による上書きを保護する設計（protected set）。
- テスト・モック用に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

### Breaking Changes
- （初版のため該当なし）

---

（以降のリリースはここに追加してください）