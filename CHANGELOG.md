CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。

注記
----
- 日付はコードベースの現在日付（生成日）を使用しています。
- 内容はリポジトリ内のソースコードから推測して記載した初版リリースの要約です。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージの初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ処理、行末コメントの扱いに対応）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス等の設定をプロパティ経由で取得可能に（必須設定未指定時は ValueError を投げる）。
  - 環境変数値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を追加。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。以下をサポート:
    - ID トークン取得（リフレッシュトークン経由）
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）
    - 401 が返った場合はトークン自動リフレッシュ（1回のみ）してリトライ
    - JSON デコード失敗時の明示的なエラーメッセージ
  - DuckDB への保存ユーティリティを実装（冪等性: ON CONFLICT DO UPDATE / DO NOTHING を使用）
    - save_daily_quotes: raw_prices テーブルへの保存（PK欠損行はスキップ）
    - save_financial_statements: raw_financials テーブルへの保存（PK欠損行はスキップ）
    - save_market_calendar: market_calendar テーブルへの保存（取引日/半日/SQ フラグを解釈）
  - 入力変換ユーティリティ (_to_float / _to_int) を追加し、非数値や不正フォーマットを安全に扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news に保存するモジュールを追加。
  - セキュリティと堅牢性に配慮した実装:
    - defusedxml を利用して XML 攻撃を軽減
    - 受信最大バイト数でメモリDoSを軽減（デフォルト 10 MB）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
    - 記事IDは正規化URLのSHA-256ハッシュ先頭を利用して冪等性を確保
    - HTTP/HTTPS 以外のスキーム拒否や SSRF 対策（IP/ホスト検証を想定）
    - バルクINSERTのチャンク化（デフォルトチャンクサイズ）
  - デフォルトRSSソース（例: Yahoo Finance の Business カテゴリ）を定義。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日MAのデータ不足時は None）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR/ウィンドウ不足時は None）
    - calc_value: per / roe を raw_financials と prices_daily から計算（財務データの最新レコード参照）
    - SQL+DuckDB ベースで営業日ギャップ（週末/祝日）に配慮したスキャンレンジを採用
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコード3未満は None）
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）
    - rank: 同順位は平均ランク処理するランク付けユーティリティを提供
  - research パッケージの __all__ を整備し主要関数を公開。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで計算した生ファクターをマージして features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装。
  - 正規化: z-score 正規化（kabusys.data.stats を利用）、±3 でクリップ。
  - 日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクションを利用、例外時は ROLLBACK を試行）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し final_score を計算、売買シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算するヘルパーを提供（シグモイド変換, 逆転, None 補完など）。
  - デフォルト重みと閾値を定義し、ユーザ提供の weights は検証・正規化して合計が 1.0 になるよう補正。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつ十分なサンプル数の場合）で BUY シグナルを抑制。
  - SELL シグナルの条件にストップロス（-8%）とスコア低下を実装。価格欠損時の判定スキップ、features 未登録の保有銘柄は score=0 と扱う挙動を定義。
  - signals テーブルへの日付単位置換で冪等性を確保（トランザクション + bulk INSERT）。

- パッケージ公開インターフェース
  - kabusys パッケージの __all__ を定義（data, strategy, execution, monitoring）。
  - strategy パッケージで build_features / generate_signals をトップレベルに公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を使用し XML パース時の脆弱性軽減を実施。
- ニュースURLの正規化とトラッキングパラメータ除去、受信サイズ制限、スキーム検査などで SSRF / DoS のリスクを低減。
- J-Quants クライアントでトークンの取り扱い（キャッシュ・自動リフレッシュ）を明確化し、allow_refresh フラグで無限再帰を回避。

Notes / Implementation details
- DuckDB を主要なデータ格納・集計に使用。SQL 内でウィンドウ関数（LAG/LEAD/AVG/COUNT）を多用しているため、DuckDB 接続を引数に取る関数群は外部DB依存が少ない設計。
- 多くの計算処理で None / 非有限値の検査（math.isfinite 等）を行い、欠損や非数値に保守的に対応。
- トランザクションを用いた日付単位の置換（DELETE → INSERT）を採用し、例外発生時の ROLLBACK を試みることで原子性を保証。
- 外部依存は最小化（標準ライブラリ中心、ただし XML の安全な処理のため defusedxml を使用）。

今後の予定（推測）
- execution/monitoring モジュールの実装（実際の発注・監視ロジック）。
- ニュースと銘柄の紐付け（news_symbols）や AI スコア生成パイプラインの追加。
- PBR・配当利回り等、バリューファクターの拡張。
- トレーリングストップや時間決済などの追加エグジット条件実装。

--- 

以上（この CHANGELOG はコードの内容から推察して作成しました。実際のコミット履歴に基づく記録が必要な場合は git の履歴情報を提供してください。）