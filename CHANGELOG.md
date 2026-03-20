Keep a Changelog に準拠した形式で、このリポジトリの初回リリース相当の変更履歴（コードから推測して作成）を日本語でまとめます。

注意: 以下は提供されたソースコードの内容から推測して記載した CHANGELOG です。実際のコミット履歴ではなく機能説明的なリリースノートになっています。

All notable changes
===================

Unreleased
----------

- 今後の変更項目やバグ修正などをここに記載してください。

0.1.0 - 2026-03-20
------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0

- 環境設定管理
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索して検出）。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理などの堅牢なパース）。
  - .env ロード時の上書き制御（override フラグ、OS 環境変数を protected として保護）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別 / ログレベル等の取得とバリデーションを行う。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
  - レート制限を守る固定間隔スロットリング（120 req/min）を実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 応答時のトークン自動リフレッシュ処理を実装（1回リフレッシュして再試行）。
  - ページネーション対応のデータ取得（株価日足 / 財務データ / マーケットカレンダー）。
  - DuckDB への冪等保存関数を実装（raw_prices / raw_financials / market_calendar に対する INSERT ... ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ (_to_float / _to_int) を追加し入力の堅牢性を確保。

- ニュース収集
  - RSS フィード収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリパラメータソート）を実装。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - defusedxml を使用した安全な XML パース、受信サイズ上限（10MB）によるメモリ保護、SSRF 等への対策（スキーム検査・IP 等のチェックのための基盤が含まれる）。
  - DB へのバルク挿入とチャンク処理（パフォーマンスと SQL パラメータ上限対策）、INSERT RETURNING による挿入数の正確取得方針。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - Value（per / roe、raw_financials から最新の財務データを取得）
  - 将来リターン計算（calc_forward_returns）を実装（任意ホライズンに対応、1/5/21 日がデフォルト）。
  - IC（Spearman の ρ）計算、rank 関数（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）を提供。
  - 外部依存（pandas 等）を使わずに標準ライブラリ + DuckDB SQL で完結する設計。

- 特徴量エンジニアリング & シグナル生成（ストラテジー）
  - features を生成する build_features を実装（src/kabusys/strategy/feature_engineering.py）。
    - research の生ファクターを取得してマージ、ユニバースフィルタ（最低株価300円、20日平均売買代金≥5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション・バルク挿入で冪等性・原子性を確保）。
  - シグナル生成モジュール generate_signals を実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き合算で計算（デフォルト重みを提供）し、閾値（デフォルト 0.60）を超える銘柄を BUY 生成。
    - Bear レジーム判定（AI レジームスコアの平均が負）で BUY を抑制。
    - エグジット（SELL）判定を実装（ストップロス -8% / final_score が閾値未満 等）。
    - positions, features, ai_scores, prices_daily を参照して SELL を決定、signals テーブルへ日付単位で置換保存。
    - 重みの入力バリデーション（未知キーや負値・非数は無視、合計が 1 でない場合は正規化して適用）。

- トランザクション耐性 / ロールバック処理
  - features / signals の挿入処理で BEGIN/COMMIT/ROLLBACK を適切に扱い、ROLLBACK 失敗時は警告ログ出力して例外を再送出する設計。

Security
- XML パースに defusedxml を利用して XML Bomb 等の攻撃を防止。
- RSS URL 正規化・スキームチェック・受信バイト上限などを導入して SSRF / メモリ DoS のリスクを軽減。
- J-Quants クライアントでトークン管理を行い、401 に対して自動リフレッシュを限定的に行うことで無限ループを回避。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Notes / Implementation details
- DuckDB をデータ層として中心に利用。各処理は DuckDB 接続を引数に取り SQL と Python で完結するよう設計されているため、本番発注層や外部 API への副作用を持たない（ルックアヘッドバイアス防止方針）。
- settings では環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を行い、不正値は明示的なエラーを投げる。
- ニュース記事 ID 生成や DB 保存は冪等性を重視している（重複挿入を避ける）。

今後の改善候補（推奨）
- feature_engineering / signal_generator の単体テスト充実（境界ケース、価格欠損時の挙動、weights の異常値処理等）。
- news_collector の全文検索や NLP 前処理（トークン化・ステミング等）との統合。
- positions テーブルに peak_price / entry_date を保存してトレーリングストップや保有期間決済条件を実装。
- J-Quants クライアントの非同期化や並列取得によるスループット向上（ただしレート制限に注意）。

-- End of CHANGELOG --