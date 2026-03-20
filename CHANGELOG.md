KEEP A CHANGELOG
=================

このファイルは Keep a Changelog のフォーマットに準拠しています。
（https://keepachangelog.com/ja/）

Unreleased
----------

- なし

0.1.0 - 2026-03-20
-----------------

Added
- パッケージ基盤
  - パッケージの初期リリース。トップレベルのバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定（cwd 非依存）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは以下に対応:
    - コメント行 / 空行を無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォートを含む値（バックスラッシュでのエスケープ考慮）
    - インラインコメントの扱い（クォートの有無に応じた適切な処理）
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得:
    - J-Quants, kabu API, Slack, DB パス、環境（development/paper_trading/live）やログレベル等
    - 必須値未設定時は ValueError を送出
    - env のバリデーション（許容値チェック）と利便性メソッド（is_live / is_paper / is_dev）

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter
    - ページネーション対応の fetch 関数（daily quotes / financial statements / market calendar）
    - リトライロジック（指数バックオフ、最大3回）および 401 受信時の自動トークンリフレッシュ（1 回のみ）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコード失敗や HTTP エラーのハンドリング
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE による重複排除
    - PK 欠損行のスキップとログ出力
    - 型変換ユーティリティ `_to_float` / `_to_int`

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存するための安全な基盤を実装:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）
    - 受信最大サイズ制限（10 MB）や SSRF 対策（HTTP/HTTPS のみ）
    - 記事 ID は URL を正規化して SHA-256 のハッシュ（先頭32文字）で生成し冪等性を確保
    - トラッキングパラメータ（utm_* 等）の除去、クエリソート、フラグメント削除による URL 正規化実装
    - バルク INSERT のチャンク処理によるパフォーマンス配慮
    - デフォルト RSS ソースとして Yahoo Finance の Business カテゴリを登録

- 研究（research）モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
    - Volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio
    - Value: per / roe（raw_financials から最新レコードを取得）
    - 営業日と祝日を考慮したスキャン範囲バッファや欠損値処理
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）：next 1/5/21 営業日等のリターンを一度のクエリで取得
    - IC（Information Coefficient）計算（calc_ic）：Spearman の ρ をランク計算（同順位は平均ランク）で実装
    - 統計サマリー（factor_summary）：count, mean, std, min, max, median を算出（None 除外）
    - ランク変換ユーティリティ（rank）：丸めによる ties の誤検出を低減する実装

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールから取得した raw factor を統合・正規化して features テーブルへ保存する処理を実装:
    - ユニバースフィルタ: 最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8（5 億円）
    - 正規化: zscore_normalize を用い、対象カラムを Z スコア化し ±3 にクリップ（_ZSCORE_CLIP=3）
    - 日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクション使用）
    - 欠損や非有限値の扱いで堅牢な実装

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア final_score を計算し signals テーブルへ保存:
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（合計 1 に再スケール）
    - BUY閾値 default 0.60、stop-loss -8%（_STOP_LOSS_RATE = -0.08）
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、かつサンプル数 >= 3 の場合に BUY を抑制
    - 欠損コンポーネントは中立値 0.5 で補完し不当な降格を防止
    - SELL 判定（保有ポジション）:
      - ストップロス（優先）
      - final_score が閾値未満のスコア低下
      - 価格欠損時は SELL 判定をスキップ（誤クローズ回避）
    - 日付単位の置換（DELETE + bulk INSERT）による冪等性（トランザクション + rollback ログ）

- モジュールエクスポート
  - strategy パッケージは build_features / generate_signals を公開
  - research パッケージは calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank を公開

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集で defusedxml を採用、RSS パース時の XML 攻撃を軽減
- ニュース URL の正規化とトラッキングパラメータ除去により同一記事の二重取り込みを抑制
- SSRF・メモリ DoS 緩和のためスキーム検証・受信サイズ制限を設ける設計方針を反映

Notes / Known limitations
- execution モジュールはパッケージに存在するが（src/kabusys/execution/__init__.py）実装は含まれていません（発注層は分離された設計）。
- news_collector.py の一部関数（ファイル末尾に続く処理）が実装途中または本抜粋で途切れている可能性があります。実運用では raw_news への保存ロジックや銘柄紐付け（news_symbols）部分の完成を要確認。
- zscore_normalize は kabusys.data.stats に依存（該当ユーティリティの実装が別モジュールに存在する前提）。
- トレーリングストップや時間決済など、一部のエグジット条件は未実装（signal_generator の docstring に明記）。
- DB スキーマ（tables）の詳細、マイグレーションは本リリースに含まれていません。DuckDB のテーブル定義に合わせて運用する必要があります。

Authors
- このリポジトリのコードから推測して作成。

License
- リポジトリ内のライセンス記載に従ってください（本 CHANGELOG では特に指定なし）。

-----