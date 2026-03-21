KEEP A CHANGELOG形式に準拠した CHANGELOG.md を日本語で作成しました。コードベースから推測可能な変更点・初期リリース内容を記載しています。

---
Unreleased
- なし

[0.1.0] - 2026-03-21
====================

Added
-----
- パッケージの初期実装を追加（kabusys v0.1.0）
  - パッケージエントリポイント: src/kabusys/__init__.py
    - __version__ = "0.1.0"
    - パブリック API: data, strategy, execution, monitoring を公開

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルの自動読み込み機能を実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応）
  - ファイル読み込み失敗時に警告出力
  - Settings クラスを実装し、必要な設定をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）
  - env / log_level の検証ロジック（有効値制約）と is_live / is_paper / is_dev ヘルパーを提供

- データ取得・永続化（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔スロットリングによるレート制限（120 req/min）を RateLimiter で実装
    - 冪等なデータ保存（DuckDB への ON CONFLICT DO UPDATE を利用）
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx に対してリトライ）
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（トークンキャッシュをモジュールレベルで共有）
    - ページネーション対応（pagination_key のループ処理）
    - データ変換ユーティリティ（_to_float, _to_int）
    - DuckDB 保存関数:
      - save_daily_quotes → raw_prices テーブルへの挿入/更新
      - save_financial_statements → raw_financials テーブルへの挿入/更新
      - save_market_calendar → market_calendar テーブルへの挿入/更新
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集・正規化（既定ソース: Yahoo Finance のビジネス RSS）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、キー順ソート）
    - defusedxml による XML パース（XML Bomb 等への対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）および SSRF 回避の設計指針
    - バルク INSERT のチャンク処理（SQL 長/パラメータ数対策）

- 研究（research）モジュール（src/kabusys/research/）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200 日データ不足時は None）
    - ボラティリティ/流動性: atr_20 / atr_pct / avg_turnover / volume_ratio（20 日ウィンドウ、データ不足時は None）
    - バリュー: per, roe（raw_financials の最新報告を使用）
    - DuckDB のウィンドウ関数を活用した高効率 SQL 実装
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターン計算、ホライズン検証）
    - calc_ic（Spearman の ρ をランク相関で算出、最小サンプル数制約あり）
    - factor_summary（count/mean/std/min/max/median の集計）
    - rank（同順位は平均ランクで処理）
  - research __init__ で主要関数を公開

- 戦略（strategy）モジュール（src/kabusys/strategy/）
  - feature_engineering.build_features
    - research モジュールの生ファクターを統合・正規化し features テーブルへ UPSERT
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装
    - Z スコア正規化（対象カラムは mom_1m,mom_3m,atr_pct,volume_ratio,ma200_dev）、±3 でクリップ
    - 日付単位で置換（トランザクション + バルク挿入で原子性を保証）
  - signal_generator.generate_signals
    - features と ai_scores を統合しコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - default weights を実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と、外部 weights の検証・リスケール処理
    - final_score の算出と BUY/SELL シグナル生成ロジック
      - BUY: final_score >= threshold（デフォルト 0.60）、Bear レジーム時は BUY を抑制
      - SELL: ストップロス（終値/avg_price - 1 < -8%）および final_score < threshold
    - Bear 判定は ai_scores の regime_score 平均が負かつ十分なサンプル数で判定
    - 日付単位で signals テーブルへ置換（トランザクション + バルク挿入）
    - SELL 優先ポリシー（SELL 対象は BUY から除外してランクを再付与）
    - ロバストな欠損処理（None / NaN / 非有限値の扱い、欠損コンポーネントは 0.5 で補完等）

- DuckDB を前提とした SQL 実装全体
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, signals, positions などを参照/更新する設計
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた原子性確保と、ROLLBACK 失敗時の警告ログ

Security
--------
- ニュースパーサで defusedxml を使用して XML に対する安全対策を実施
- news_collector で URL 正規化とトラッキングパラメータ削除、HTTP(S) スキームの許可方針など SSRF/トラッキング対策の記載あり
- J-Quants クライアントでトークン/ヘッダ処理、認証リフレッシュの制御あり

Changed
-------
- 初回リリースのため該当なし

Deprecated
----------
- なし

Removed
-------
- なし

Fixed
-----
- 初回リリースのため該当なし

Notes / Known limitations
-------------------------
- signal_generator 内の未実装機能（今後の実装予定として明示）
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の記事 ID 生成（SHA-256 ハッシュ等）や銘柄紐付け処理は設計に記載されているが、このスナップショットでは一部実装が省略されている可能性あり（コードの続きに依存）。
- J-Quants API のリトライ対象は 408/429/5xx。429 の場合は Retry-After ヘッダを優先的に利用。
- env パーサは多くのケースに対応しているが、極端に複雑な .env の構文は想定外の挙動をする可能性あり。
- DuckDB のスキーマ（テーブル定義）はこの変更履歴に含まれていないため、実行には期待されるテーブル定義が必要。

Acknowledgements
----------------
- 本 CHANGELOG は提示されたソースコードから推測して作成しています。リリースノートの最終確定には実際のコミット履歴・リリース作業ログを参照してください。

---