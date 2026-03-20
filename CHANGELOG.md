CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

リリースノートは主にコードベース（src/ 以下）から推測して作成しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
  - 高度な .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの値でのインラインコメント判定（直前が空白/タブの場合のみ '#...' をコメント扱い）。
    - 不正行やキー欠損行を安全に無視。
  - Settings クラスにアプリケーション設定を集約（J-Quants / kabu API / Slack / DB パス / env / log_level 等）。入力検証（KABUSYS_ENV / LOG_LEVEL の許容値検査）と利便性プロパティ（is_live/is_paper/is_dev）を提供。
  - 必須環境変数が未設定の場合は明示的な ValueError を報告。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限対応（120 req/min）。
    - 冪等性のある DuckDB への保存（ON CONFLICT DO UPDATE）を提供する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - ページネーション対応のフェッチ（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 時は Retry-After を尊重。
    - 401 Unauthorized 受信時はトークン自動リフレッシュ（1 回のみ）して再試行。
    - 取得時刻 fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアス追跡を容易に。
    - モジュールレベルの ID トークンキャッシュでページネーション間のトークン共有を最適化。
  - 型安全なユーティリティ (_to_float / _to_int) により外部入力の堅牢なパースを実現。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集モジュールを追加（デフォルトで Yahoo Japan のビジネスカテゴリ RSS を含む）。
  - セキュリティ配慮:
    - defusedxml を用いた XML パースで XML Bomb 等を防止。
    - HTTP/HTTPS スキームのみ許可、SSRF リスクを低減するための妥当性検査を想定。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を回避。
  - URL 正規化機能:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、スキーム/ホストの小文字化、フラグメント削除、クエリのソート。
    - 正規化後の URL を基に記事ID を（設計上） SHA-256 ハッシュ化して冪等に保存する方針（raw_news への重複防止）。
  - テキスト前処理（URL 除去、空白正規化）と、バルク INSERT のチャンク処理で DB オーバーヘッドを抑制。
  - INSERT RETURNING を使って実際に挿入された件数を正確に返す設計（SQL 実装想定）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュールを追加（calc_momentum / calc_volatility / calc_value）。
    - Momentum: 約1ヶ月/3ヶ月/6ヶ月リターン、200日移動平均乖離(ma200_dev)（データ不足時は None）。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: raw_financials から最新財務を取得して PER, ROE を計算（EPS==0 は None）。
    - DuckDB のウィンドウ関数を活用し、営業日欠損（週末・祝日）に対するバッファ範囲を確保。
  - 特徴量探索モジュール（feature_exploration）を追加:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、最小サンプル要件あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティ（丸め誤差対策で round で正規化）。

- 戦略（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（feature_engineering.build_features）:
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（最低株価/最低売買代金）適用、Z スコア正規化（zscore_normalize を利用）→ ±3 でクリップして features テーブルに UPSERT（トランザクションで日付単位の置換）する実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算、重み付け合算して final_score を算出（デフォルト重みを実装）。
    - AI レジームスコアの集計による Bear 判定（サンプル閾値あり）。Bear 時は BUY を抑制。
    - BUY: final_score >= デフォルト閾値 0.60（閾値・重みは引数で上書き可能だが妥当性検査あり）。
    - SELL（エグジット）: ストップロス（-8%）およびスコア低下判定を実装。ポジションが features にない場合は score=0 と見なして SELL 判定。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。

- データ統計ユーティリティ（src/kabusys/data/stats.py を想定して利用）
  - zscore_normalize を研究/戦略層で利用する設計（モジュールの出口は research/__init__.py で再エクスポート）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml を用いた RSS パース、URL スキーム検査、受信サイズ制限などにより外部入力に対するセキュリティ考慮を実装。
- J-Quants クライアントのトークン自動リフレッシュとリトライによる堅牢化。

Notes / Implementation details
- DuckDB をデータ層として前提（prices_daily / raw_financials / features / ai_scores / positions / signals / raw_prices / raw_financials / market_calendar 等のテーブルを利用）。
- 多くの DB 操作はトランザクション＋バルク挿入で「日付単位の置換（DELETE->INSERT）」を行い、原子性と冪等性を保証する設計。
- ルックアヘッドバイアス防止方針が一貫しており、target_date 以前の「利用可能な最新データ」のみ参照する実装になっている。
- ロギングを適所に設置（info/warning/debug）し、異常系（価格欠損、PK 欠損行スキップ、ROLLBACK 失敗など）で明示的なログを出力。

互換性 / 破壊的変更
- 初回リリースのため既存互換性に関する破壊的変更はなし。

今後の改善候補（コードから推測）
- feature_engineering や signal_generator のユニットテスト追加。
- ニュース記事 → 銘柄コード紐付け（news_symbols）の具現化と NER/マッチング精度向上。
- positions テーブルに peak_price / entry_date を追加してトレーリングストップや時間決済を実装。
- 監視・モニタリング（monitoring）および execution 層の実装と統合テスト。

--- 

注: 本 CHANGELOG は提供されたソースコード（コメント・実装）から推測して作成しています。実際のリポジトリ履歴（コミットメッセージ等）に基づくものではありません。必要であれば、より細かいファイル別・関数別の変更点や実装上の制約を追記します。