# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムの基礎機能を実装しました。主な追加点は以下の通りです。

### 追加
- パッケージの骨組み
  - kabusys パッケージを追加。モジュール構成は data / research / strategy / execution / monitoring（__all__ に公開）。
  - バージョンは 0.1.0 に設定。

- 設定・環境変数管理
  - 環境変数を管理する settings を実装（kabusys.config.Settings）。
  - .env 自動読み込み機能を実装：プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込み。
  - .env パーサを堅牢に実装（コメント・export プレフィックス・クォート・エスケープに対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require を実装。
  - 設定項目（J-Quants トークン、kabuAPI パスワード、Slack トークン・チャンネル、DB パス、環境種別・ログレベル判定ユーティリティ等）を提供。

- Data レイヤー
  - J-Quants API クライアント（kabusys.data.jquants_client）を実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（指数バックオフ）と 401 時の自動トークンリフレッシュに対応。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT/DO UPDATE により重複を吸収。
    - 型変換ユーティリティ（_to_float, _to_int）を用意。
  - ニュース収集モジュール（kabusys.data.news_collector）を実装。
    - RSS 取得→正規化→raw_news への冪等保存の処理方針を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、フラグメント除去、クエリソート）。
    - セキュリティ対策：defusedxml による XML パース、受信サイズ上限、SSRF 回避等を設計に組み込む。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。

- Research（研究）機能
  - ファクター計算・探索モジュールを実装（kabusys.research）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。ウィンドウ不足時は None を返す。
    - calc_volatility: 20 日 ATR・相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials（直近の財務）と prices_daily を組み合わせて PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足（<3 件）や分散ゼロは None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めで ties 検出誤差を低減）。
  - すべて DuckDB の prices_daily / raw_financials のみを参照し、本番 API へアクセスしない設計。

- Strategy（シグナル生成）
  - feature_engineering:
    - research 側で算出した raw ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（外れ値は ±3 でクリップ）して features に UPSERT（日付単位で置換）する。
    - 処理はルックアヘッドバイアスを避けるよう target_date 時点のデータのみを使用。
  - signal_generator:
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL のシグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）を個別に計算するユーティリティを実装（シグモイド変換や PER 特殊処理等）。
    - デフォルト重みや閾値（threshold=0.60）を定義し、ユーザ渡しの weights を検証・補完・リスケールするロジックを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。ただし最小サンプル数を設定し誤判定を回避）を実装し、Bear 時は BUY を抑制。
    - SELL 条件（ストップロス -8% / final_score が threshold 未満）を実装。保有銘柄価格欠損時の判定スキップや features 未登録銘柄の扱い（score=0 として SELL）の方針を明確化。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性と原子性を確保。
    - positions テーブルの一部条件（ピーク価格やエントリー日が必要なトレーリングストップ等）は未実装として文書化。

### 設計上の注意 / 方針（ドキュメントに明示）
- ルックアヘッドバイアス防止: Strategy / Research の全関数は target_date 時点で「利用可能なデータのみ」を使用する設計。
- 再現性・監査性: データ取得時に fetched_at を UTC で記録し、いつデータが取得されたかを追跡可能にする。
- 冪等性: DB への挿入は可能な限り ON CONFLICT / 日付単位の削除→挿入で実装。
- セキュリティと堅牢性: XML パースの安全化、.env パースの堅牢化、HTTP エラーハンドリング（リトライ/バックオフ/Retry-After）、入力検証を重視。

### 既知の未実装点 / 今後の拡張候補
- strategy の SELL 条件におけるトレーリングストップ・時間決済は positions テーブルに peak_price / entry_date 情報が必要であり未実装。
- research の一部ファクター（PBR、配当利回りなど）は未実装。
- news_collector の RSS パースから DB への実際のマッピング処理（news_symbols への紐付け等）は詳細実装が残る可能性あり。

### 互換性の注意（Breaking Changes）
- 初回リリースのため既知の破壊的変更はありません。

---

今後のリリースでは以下を検討しています:
- execution 層とのインテグレーション（kabu API を用いた実際の発注処理）
- モニタリング・アラート機能（Slack 通知等）の追加
- 追加ファクター・機械学習モデルの統合（ai_scores の生成フロー）