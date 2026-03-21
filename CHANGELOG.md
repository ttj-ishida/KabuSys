CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式に従って記載しています。  
このファイルは、パッケージ kabusys のコードベース（初期リリース相当）から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 0.1.0: 初回公開相当の機能と実装の概要

Unreleased
----------
- なし（初回リリースのみを記載）

[0.1.0] - 2026-03-21
--------------------
Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - サブパッケージ: data, research, strategy, execution, monitoring（__all__ に登録）。

- 環境設定管理 (kabusys.config)
  - Settings クラスを実装し、環境変数から主要設定を取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env パーサーを強化:
    - 空行・コメント行（#）の処理
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォートなしでの行内コメント判定（直前が空白/タブの場合のみ）
  - 環境値検証:
    - KABUSYS_ENV は {development,paper_trading,live} のみ許容
    - LOG_LEVEL は標準的なログレベル文字列のみ許容
  - デフォルト値:
    - KABUSYS_API_BASE_URL のデフォルトや DuckDB/SQLite のパス（data/ 配下）を提供

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（取得: 日足, 財務データ, マーケットカレンダー）。
  - レートリミッタ実装（120 req/min、固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 応答時はトークンを自動リフレッシュして 1 回だけ再試行。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - DuckDB へ冪等保存するユーティリティを追加:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - fetch_*/save_* 系のログ出力（取得件数、スキップ件数等）を充実。
  - HTTP/JSON ラッパーで JSON デコード失敗時のエラー診断を強化。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、不正データを None に正しく変換。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news / news_symbols へ保存する基盤を実装。
  - URL 正規化機能を実装（小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設定してメモリDoSを軽減
    - トラッキングパラメータ除去（utm_*, fbclid 等）
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
    - DB 保存はトランザクションでまとめ、バルク挿入（チャンク）で効率化
  - INSERT RETURNING を用いることで挿入件数を正確に把握

- リサーチモジュール (kabusys.research)
  - factor_research: prices_daily/raw_financials から計量ファクターを計算
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均）
    - Volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、volume_ratio
    - Value: per, roe（raw_financials から最新の財務データを参照）
    - カレンダーバッファを用いた範囲スキャン設計（営業日 ≒ カレンダー日 × 2 のバッファ）
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman のランク相関（IC）を実装（有効レコードが 3 未満の場合は None）
    - rank: 同順位は平均ランク処理、丸め誤差を避けるため round(..., 12) を利用
    - factor_summary: count/mean/std/min/max/median の統計サマリを提供
  - 全関数は DuckDB 接続を受け取り外部ライブラリに依存しない実装

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で計算した raw factor を統合して features テーブルへ保存する処理を実装
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
  - 正規化:
    - 指定列を zscore_normalize で正規化し ±3 でクリップ（外れ値抑制）
  - DB 操作は日付単位で削除→挿入のトランザクションで原子性を保証（冪等）

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算、signals テーブルへ書き込む
  - 統合スコアのデフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
  - BUY 閾値デフォルト 0.60、stop_loss は -8% を採用
  - コンポーネントスコアの計算:
    - モメンタム: momentum_20/60, ma200_dev を sigmoid -> 平均化
    - Value: per を 20 を基準にスケーリング（低 PER が高スコア）
    - Volatility: atr_pct を反転して低ボラを高スコアに
    - Liquidity: volume_ratio を sigmoid
    - AI news: ai_score を sigmoid、未登録は中立扱い
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止
  - Bear レジーム判定:
    - ai_scores の regime_score 平均が負なら Bear（ただし検出には最小サンプル数 3 を要求）
    - Bear 場合は BUY シグナルを抑制
  - SELL シグナル（エグジット）実装:
    - stop_loss（終値/avg_price - 1 < -8%）
    - final_score が threshold 未満（score_drop）
    - 保有中の銘柄の価格欠損時は SELL 判定をスキップして誤クローズを回避
    - SELL は BUY より優先され、signals テーブルへ日付単位で原子置換
  - DB 操作はトランザクション + バルク挿入で冪等性を保つ

Changed
- ログ・警告の充実
  - 各処理で警告・情報ログを追加（例: .env 読み込み失敗、PK 欠損でのスキップ、ROLLBACK 失敗の警告など）
- 重み指定の堅牢化（generate_signals）
  - ユーザー指定の weights を検証（未知キー・非数値・負値・NaN/Inf を無視）
  - 合計が 1.0 でない場合は自動再スケール、合計が 0 以下ならデフォルトにフォールバック

Fixed
- DB 保存時の冪等性を徹底
  - raw_* / market_calendar の INSERT に ON CONFLICT DO UPDATE を採用
  - features / signals は日付単位で DELETE→INSERT を行い原子性を確保（トランザクション）

Security
- 外部データ取り込みでの安全策を強化
  - news_collector: defusedxml による XML パース、受信サイズ制限、URL 正規化・トラッキング削除で SSRF/XSS 等のリスクを低減
  - jquants_client: トークン管理と 401 時の安全な再取得（無限再帰を防止する allow_refresh フラグ）

Known issues / Not implemented
- signal_generator 側の未実装・保留点（コメントに明記）
  - トレーリングストップ（peak_price が positions に必要）、時間決済（保有 60 営業日超過）は未実装
- factor_research の calc_value: PBR・配当利回りなどの追加指標は現バージョンでは未対応
- news_collector の一部細部（例: gzip ハンドリング等）は将来的な改善余地あり（import は存在）

Notes / Design decisions
- ルックアヘッドバイアス対策を各モジュールで意識:
  - データ取得時に fetched_at を記録
  - feature/signal の計算は target_date 時点で利用可能なデータのみを参照
- 外部ライブラリへの依存を最小化（research モジュールは標準ライブラリのみで実装）
- DuckDB を中心とした SQL + Python の処理設計で大規模データへの高速処理を意図

クレジット
- 本 CHANGELOG は、コードベースの実装内容（docstring とソース）から機能・設計方針を推測して作成しました。実際のリリースノートとして使用する前に、実際のコミット履歴やリリース日等を確認してください。