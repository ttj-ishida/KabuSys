# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

次の凡例に従います: Added, Changed, Deprecated, Removed, Fixed, Security。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース "KabuSys"（バージョン 0.1.0）。
  - パッケージトップ: `src/kabusys/__init__.py` にバージョン情報と公開モジュール一覧（data, strategy, execution, monitoring）を追加。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env 自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない実装。
  - 自動ロード無効化用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env の堅牢なパーサーを実装（コメント・export プレフィックス・シングル/ダブルクォート内のエスケープ処理・インラインコメントの扱い等に対応）。
  - OS の既存環境変数を保護する仕組み（protected set）を導入し、`.env.local` の上書き制御を実現。
  - 必須環境変数取得ヘルパ `_require` と、Settings クラスを提供。J-Quants/J-Quants refresh token、kabuステーション API パスワード、Slack トークン/チャンネル、DBパス（DuckDB/SQLite）、環境種別検証（development/paper_trading/live）、ログレベル検証などのプロパティを提供。

- データ取得/保存（J-Quants クライアント）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。主な機能:
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）とステータス別の扱い（408/429/5xx の再試行管理、429 の Retry-After の尊重）。
    - 401 応答時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応でのデータ取得。
    - API: `get_id_token`, `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
  - DuckDB 保存関数を実装（冪等性を考慮した upsert）:
    - `save_daily_quotes` → `raw_prices`（ON CONFLICT DO UPDATE）
    - `save_financial_statements` → `raw_financials`（ON CONFLICT DO UPDATE）
    - `save_market_calendar` → `market_calendar`（ON CONFLICT DO UPDATE）
  - Look-ahead bias 対策: 取得時刻を UTC（ISO8601）で `fetched_at` に記録。
  - 入力パース補助: `_to_float`, `_to_int`（厳密な変換ポリシー）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集パイプラインを実装（デフォルトは Yahoo Finance のカテゴリ RSS を登録）。
  - 実装方針/特徴:
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、クエリキーソート、フラグメント除去など。
    - XML パースに defusedxml を利用して XML Bomb 等の脅威を軽減。
    - HTTP 受信サイズの上限（10MB）を設定してメモリ DoS を防止。
    - SSRF 対策（HTTP/HTTPS のみ想定）やトラッキングパラメータ除去等の前処理を実装。
    - DB へのバルク挿入はチャンク化（チャンクサイズ 1000）して効率化。
    - raw_news / news_symbols 等の保存（ON CONFLICT DO NOTHING 等を想定）と銘柄紐付けを想定した設計。

- リサーチ（研究）機能（src/kabusys/research）
  - ファクター計算モジュール（factor_research.py）:
    - `calc_momentum`：1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - `calc_volatility`：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - `calc_value`：raw_financials と当日の株価を組み合わせて PER/ROE を計算。
    - DuckDB 上の prices_daily / raw_financials テーブルのみを参照する仕様で、外部 API には依存しない。
  - 特徴量探索（feature_exploration.py）:
    - `calc_forward_returns`：指定ホライズン（デフォルト [1,5,21]）の将来リターン算出。
    - `calc_ic`：スピアマンランク相関（IC）計算。最小サンプル制約あり（<3 は None）。
    - `factor_summary`：count/mean/std/min/max/median を算出する統計サマリー。
    - `rank`：同順位は平均ランクとするランク付けを実装（丸め処理で ties の検出漏れを抑制）。
  - research パッケージの __init__ で主要関数を公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - `build_features(conn, target_date)` を実装:
    - research 側の `calc_momentum`, `calc_volatility`, `calc_value` と連携して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップ。
    - features テーブルへの日次置換（DELETE → INSERT）をトランザクションで行い冪等性を確保。
    - 欠損・非有限値の扱いに注意した実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装:
    - features, ai_scores, positions を参照して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や PER の逆数変換等でスコア化。
    - デフォルトの重みを定義し、ユーザ渡しの weights は妥当性チェック・正規化（合計 1.0 に再スケール）を行う。
    - Bear レジーム検知（ai_scores の regime_score 平均が負）で BUY シグナルを抑制。
    - BUY/SELL の生成ロジック:
      - BUY: final_score >= threshold（Bear 時は抑制）
      - SELL: ストップロス（終値 / avg_price - 1 < -8%）および final_score の低下
      - 保有銘柄で価格欠損の際は SELL 判定をスキップするなどの安全策
    - SELL 優先ポリシー: SELL 対象を BUY から除外し、BUY ランクを再付与。
    - signals テーブルへの日次置換（DELETE → INSERT）をトランザクションで行い冪等性を確保。
    - 戦略仕様（StrategyModel.md）のセクションに基づいた設計と明示的な未実装事項（トレーリングストップ、時間決済など）をドキュメント内に記載。

- 汎用ユーティリティ
  - Rank/スコア算出関数、_sigmoid、平均化の扱い、欠損値の中立補完（0.5）など、戦略評価の一貫性を保つユーティリティを複数実装。
  - ロギングの適切な利用（警告・情報・デバッグメッセージ）。

### Changed
- （該当なし）初回リリースのため履歴変更なし。

### Fixed
- （該当なし）初回リリースのため修正履歴なし。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- news_collector で XML パースに defusedxml を採用し、XML に起因する脆弱性を軽減。
- ニュースの URL 正規化によりトラッキングパラメータを除去、SSRF や追跡によるリスクを緩和する方針を採用。
- HTTP 応答サイズの上限（10MB）でメモリ DoS を抑制。
- J-Quants クライアントでは 401 自動リフレッシュおよびリトライ戦略を明示し、不正な再試行ループを避ける実装。

### Notes / Requirements / DB schema expectations
- DuckDB 上に以下のテーブル（スキーマ）は本実装が正しく動作する前提:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等。
- 多くの関数は「target_date 時点のデータのみを用いる」方針（ルックアヘッドバイアス対策）に基づく。
- 一部機能（例: news <-> symbol マッチング、positions の peak_price/entry_date を用いるトレーリングストップ等）は今後の拡張対象としてドキュメントに記載。
- 環境変数やファイルパスの設定は Settings 経由で取得するため、.env.example を元に .env を用意することが推奨。

---

本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際の設計文書（StrategyModel.md / DataPlatform.md など）や運用ルールに従って補足・修正してください。