CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

[0.1.0] - 2026-03-19
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 自動 .env 読み込み（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env 行パーサは以下に対応:
    - 空行 / コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート外のインラインコメント扱い（直前が空白/タブの場合）
  - Settings クラスを提供し、必要な環境変数取得メソッドを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等の必須キー検証
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
    - KABUSYS_ENV の列挙検証（development / paper_trading / live）
    - LOG_LEVEL の列挙検証（DEBUG/INFO/...）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（pagination 対応）。
  - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回）。429 の場合は Retry-After を優先。
  - 401 応答時にリフレッシュトークンで自動的にトークン更新して 1 回リトライ。
  - ページネーションを考慮した id_token キャッシュ共有実装。
  - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB 保存用: save_daily_quotes, save_financial_statements, save_market_calendar を実装（冪等性: ON CONFLICT DO UPDATE）。
  - データ変換ユーティリティ: _to_float / _to_int（不正値は None に変換）。
  - 取得・保存時のログ出力・欠損 PK 行の警告。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集の基盤実装（RSS ソース定義・XML パース・記事正規化・DB 保存方針）。
  - セキュリティ考慮（defusedxml の使用、受信サイズ上限、HTTP スキーム検証、SSRF 対策を意識した設計）。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成する方針。
  - トラッキングパラメータ除去（utm_* 等）、URL 正規化実装の下地（_normalize_url）。
  - バルク INSERT チャンクサイズや INSERT RETURNING を意識した設計。

- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）を実装:
    - calc_momentum: 1/3/6 ヶ月リターン、MA200 乖離率（データ不足時 None）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials から直近財務データを取得）
    - SQL + DuckDB ウィンドウ関数を利用した実装
  - 特徴量探索（kabusys.research.feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。サンプル不足時は None。
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 平均ランク処理（同順位は平均ランク、丸めによる ties 対策）

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の生ファクターを統合・ユニバースフィルタ（最低株価・最低平均売買代金）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入、冪等）
    - 価格参照は target_date 以前の最新価格を使用（ルックアヘッドバイアス対策）
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して final_score を計算（momentum/value/volatility/liquidity/news の重み合成）
    - デフォルト重み・閾値を定義（デフォルト閾値 = 0.60）
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0、サンプル閾値あり）により BUY を抑制
    - BUY 条件: final_score >= threshold（Bear の場合は抑制）
    - SELL 条件（エグジット）:
      - ストップロス: 現在価格が avg_price に対して -8% 以下
      - スコア低下: final_score < threshold
    - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクション処理）
    - 欠損ファクターの扱い: None のコンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格を防ぐ）
    - 重み入力は検証（未知キー・非数値・負値などは無視）、合計が 1.0 でなければ再スケール

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- news_collector で defusedxml を利用、受信サイズ制限、トラッキングパラメータ除去、スキームチェックなど SSRF / XML Bomb / メモリ DoS を考慮した実装設計を導入。
- jquants_client の HTTP エラー処理で 401 リフレッシュやリトライ制御を実装し、誤ったトークン状態での露出を低減。

Deprecated
- なし

Removed
- なし

Known limitations / TODOs
- signal_generator のエグジット条件:
  - トレーリングストップ（直近最高値ベース）や時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector はこのバージョンで一部関数実装の下地を含む（RSS パース/正規化周りは追加実装が想定される）。
- 外部依存: DuckDB と defusedxml などが想定される（インストール必須）。
- 本実装はデータ操作を DuckDB に依存。実行時に適切なスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）の準備が必要。

Notes
- 全体設計方針として「ルックアヘッドバイアス回避」「発注層への依存排除」「冪等性」「トランザクションによる原子性保証」を一貫して採用しています。