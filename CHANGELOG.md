Keep a Changelog — kabusys

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
- なし

[0.1.0] - 2026-03-20
Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョンを 0.1.0 として公開、主要サブパッケージを __all__ でエクスポート。
- 環境設定/読み込み:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
    - プロジェクトルート(.git または pyproject.toml) を起点に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - OS 環境変数を保護する protected 機構、.env.local は .env を上書きする実装。
    - 必須環境変数チェック(_require)、KABUSYS_ENV / LOG_LEVEL の検証ロジック、パス設定（duckdb/sqlite）用プロパティ。
- データ取得・保存（J-Quants）:
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - HTTP リトライ（指数バックオフ、最大 3 回）、特定ステータス（408/429/5xx）での再試行、429 の場合は Retry-After を尊重。
    - 401 を受けた場合のリフレッシュトークンによる自動再取得（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT で更新）。
    - データ変換ユーティリティ（_to_float/_to_int）、UTC の fetched_at 記録など Look-ahead バイアス対策を考慮。
- ニュース収集:
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集・正規化し raw_news に保存するモジュール。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）/記事ID は正規化 URL の SHA-256 による生成で冪等性を保証。
    - defusedxml を用いて XML 攻撃を防止。
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）、SSRF 対策用の URL/スキーム検証、バルク INSERT のチャンク化で性能と安全性を確保。
- 研究用ファクター計算:
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の window 関数を活用し、過去 N 行（営業日）ベースで計算。データ不足時に None を返す扱い。
    - MA200、ATR20、出来高比、20日平均売買代金、PER/ROE 取得ロジック等を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、スピアマンの IC 計算(calc_ic)、ファクター統計サマリー(factor_summary)、rank ユーティリティを提供。
    - rank 関数は同順位を平均ランクで処理し、丸め誤差対策として round(..., 12) を用いる。
  - src/kabusys/research/__init__.py で上記 API を公開。
- 特徴量エンジニアリング:
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールから raw ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 選択した数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize）し ±3 でクリップ。
    - 日付単位で features テーブルへ置換（DELETE + INSERT）して冪等性を維持。
- シグナル生成:
  - src/kabusys/strategy/signal_generator.py
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア(momentum/value/volatility/liquidity/news)を計算し、重み付き合算で final_score を算出。
    - デフォルト重みと閾値（threshold=0.60）を持ち、ユーザ指定 weights を検証・正規化して合計が 1.0 に再スケール。
    - AI レジームスコアの平均が負なら Bear レジームとして BUY を抑制（サンプル不足時は Bear と見なさない）。
    - SELL ロジック（ストップロス -8% / final_score が閾値未満）を実装。価格欠損時は判定をスキップし誤クローズを防止。
    - signals テーブルへ日付単位の置換で書き込み（冪等）。
- 研究と戦略 APIの組み合わせ:
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
- その他:
  - src/kabusys/execution パッケージのプレースホルダを追加（将来的な発注実装向け）。

Security
- defusedxml を利用した RSS パースによる XML 攻撃対策を実装（news_collector）。
- URL 正規化・スキーム検査・受信サイズ制限などで SSRF / メモリ DoS を軽減。
- J-Quants クライアントでのトークン自動再取得は 1 回に制限し、無限再帰を防止。

Performance
- API レート制限の遵守（固定間隔スロットリング）と指数バックオフによる安定化。
- DuckDB に対するバルク挿入／ON CONFLICT 更新／トランザクションでの日付単位置換により I/O と整合性を最適化。
- news_collector でのチャンク挿入により SQL パラメータ制限に対応。

Known limitations / Not implemented
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は未実装（positions に peak_price / entry_date が必要）。
- research / strategy では外部依存（pandas 等）を避け、標準ライブラリ + DuckDB SQL を中心に実装しているため、一部の便利関数は将来拡張の余地あり。
- execution 層（発注 API への接続）は未実装で、signals テーブルまでの出力が本リリースの範囲。

Notes for users
- .env からの自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後にテスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）は Settings を通じて取得され、未設定時は ValueError が発生します。
- DuckDB / SQLite のデフォルトパスは data/ 以下に設定されていますが、環境変数で上書き可能です。

----

このバージョンは初期リリースであり、今後のリリースで execution 層実装、追加のエグジット条件、監視・運用機能（Slack 通知等）を追加予定です。