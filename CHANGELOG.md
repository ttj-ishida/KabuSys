# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

なお、本リポジトリのバージョンはパッケージメタデータ（kabusys.__version__）に合わせて 0.1.0 を初期リリースとしています。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-03-20
初回リリース。日本株の自動売買システムのコアライブラリを追加しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ宣言とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パブリック API エクスポート: data, strategy, execution, monitoring を __all__ に登録。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの強化:
    - export KEY=val の形式対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - インラインコメントの扱い（クォートあり/なしでの違い）を考慮。
  - .env 読み込み時に OS 環境変数を保護する protected 機能（.env.local は override=True だが protected キーは上書きされない）。
  - 必須環境変数チェック用の _require ユーティリティ。
  - 設定プロパティの実装（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パスのデフォルト、KABUSYS_ENV / LOG_LEVEL の検証、is_live / is_paper / is_dev 判定など）。

- データ収集 / 保存（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - HTTP リトライ（指数バックオフ）、対象ステータスコード（408/429/5xx）に対する再試行。
    - 401 Unauthorized 受信時のリフレッシュトークンによる id_token 自動更新（1回のみリトライ）。
    - ページネーション対応（pagination_key を用いたループ）。
    - fetch_* 系関数: 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - fetched_at を UTC ISO8601 で記録（Look-ahead bias のトレース用）。
      - ON CONFLICT DO UPDATE を用いた冪等保存。
      - PK 欠損行のスキップと警告ログ。
    - 安全な数値変換ユーティリティ（_to_float / _to_int）。
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードから記事収集、raw_news への冪等保存を提供。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
    - defusedxml を利用して XML 攻撃（XML Bomb 等）を緩和。
    - SSRF を防ぐため HTTP/HTTPS チェックや受信先検証を実装（設計方針）。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）とトランザクション単位での保存、INSERT RETURNING を想定した正確な挿入数管理。
    - デフォルト RSS ソース（Yahoo Finance business）を用意。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を DuckDB SQL で計算。
    - ボラティリティ/流動性: atr_20（20日ATR）、atr_pct（ATR/価格）、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。
    - バリュー: per, roe を raw_financials と prices_daily を組み合わせて算出（最新財務レコードを report_date <= target_date で取得）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API/実取引には依存しない設計。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト 1,5,21 営業日）に対する将来終値からのリターンを算出。範囲を限定して１クエリで取得することでパフォーマンス配慮。
    - IC（Information Coefficient）計算（calc_ic）：factor と将来リターンのスピアマンランク相関を計算。データ不足（有効ペア < 3）時は None を返す。
    - ランク関数（rank）：同順位は平均ランクを採る実装（四捨五入で ties の漏れを防ぐ）。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究環境で計算した raw ファクターを正規化・合成し、features テーブルへ保存する build_features を実装。
  - 処理フロー:
    - research の calc_momentum / calc_volatility / calc_value を利用して生ファクター取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize）し ±3 でクリップ。
    - DuckDB トランザクションで日付単位の置換（DELETE + bulk INSERT）を行い原子性を保証。例外時は ROLLBACK を試行し、失敗時は警告ログ。
  - 設計上、発注層や execution 層には依存しない（ルックアヘッドバイアス回避のため target_date 時点でのデータのみ使用）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - 特徴:
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算するユーティリティ関数を提供（シグモイド変換, None は中立 0.5 で補完）。
    - デフォルト重みは StrategyModel.md の値を採用。ユーザー指定 weights を受け付け、検証・フィルタ・再スケールを行う（未知キー除外、非数値/負値スキップ、合計が 1.0 でない場合は正規化）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数が閾値を満たす場合）により BUY シグナルを抑制。
    - エグジット判定（_generate_sell_signals）を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が threshold 未満のときに SELL。
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止。
      - positions テーブルの情報を元に最新ポジションを参照。
      - トレーリングストップ / 時間決済 は未実装（要 peak_price / entry_date）。
    - signals テーブルへの日付単位置換（DELETE + INSERT）をトランザクションで実行し冪等性を保証。

- パッケージ API エクスポート（kabusys.strategy, kabusys.research）
  - strategy.__init__ で build_features / generate_signals を公開。
  - research.__init__ で主要ユーティリティをエクスポート（calc_momentum 等、zscore_normalize の再公開）。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Security
- 外部データ取り込みに関する安全対策を多数導入:
  - news_collector: defusedxml の採用、受信サイズ制限、トラッキングパラメータ除去、URL 正規化・検証（SSRF 対策を考慮）。
  - jquants_client: ネットワーク障害や HTTP 異常に対する堅牢なリトライとトークンリフレッシュ処理。
  - .env 読み込み時に OS 環境変数を保護する設計（protected set）。

### Notes / Design decisions
- ルックアヘッドバイアス対策:
  - データの fetched_at を UTC で記録し、いつデータが利用可能になったかを追跡可能にした。
  - 特徴量計算・シグナル生成は target_date 時点で利用可能なデータのみを使用するよう実装。
- 冪等性:
  - DuckDB へのデータ保存は ON CONFLICT DO UPDATE / 日付単位の DELETE+INSERT を用いて冪等性を確保。
- ロギング:
  - 各主要処理は logger を経由して情報・警告・デバッグを出力する設計。
- 外部依存:
  - 研究用ユーティリティは pandas 等外部ライブラリに依存しない実装方針（標準ライブラリ + duckdb を想定）。

---

以上が初回リリース（0.1.0）の主要な変更点・追加機能の要約です。詳細な設計や仕様はソース内の docstring / コメント（StrategyModel.md / DataPlatform.md 等参照）を参照してください。