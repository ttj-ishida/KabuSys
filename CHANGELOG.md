# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

注: この CHANGELOG は与えられたコードベースから推測して作成したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - pakage メタ情報を定義（kabusys.__version__ = "0.1.0"）。
  - public API を導出する __all__（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env および環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサー実装（コメント対応、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ処理、インラインコメント処理）。
  - _load_env_file による protected（OS 環境）キー保護と override ロジック。
  - Settings クラスで主要設定値を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - Slack の設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 環境種別（KABUSYS_ENV）の検証（development / paper_trading / live）
    - ログレベル（LOG_LEVEL）の検証（DEBUG/INFO/...）
    - ヘルパープロパティ is_live / is_paper / is_dev

- Data API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得機能を実装（株価日足 / 財務データ / 市場カレンダー）。
  - 固定間隔スロットリングによるレート制限制御（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 の Retry-After 優先）。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ共有。
  - ページネーション対応（pagination_key を利用）。
  - DuckDB へ冪等保存するユーティリティ:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE
  - データ変換ユーティリティ _to_float / _to_int（安全な型変換、空値や不正文字列の扱い）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と raw_news への冪等保存処理を実装（デフォルトソースに Yahoo Finance を含む）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリパラメータソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - defusedxml による XML パース（XML Bomb 等への防御）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を防止。
  - SSRF 回避のための注意（HTTP/HTTPS のみ許容などの方針が明記されている）。
  - INSERT のチャンク化とトランザクションで性能と一貫性を担保。

- 研究（research）モジュール
  - factor_research: DuckDB の prices_daily / raw_financials を用いたファクター計算を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足時は None を返す。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御で過大評価を防止。
    - calc_value: target_date 以前の最新財務データを結合して per, roe を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得するクエリ実装。
    - calc_ic: スピアマンのランク相関（IC）計算（欠損 / サンプル不足時の None 返却）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 平均ランク（同順位は平均ランク）を計算。浮動小数丸めを用いて ties の誤検出を軽減。

  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへ日付単位で置換（削除->挿入）しトランザクションで原子性を担保。
    - 欠損・非有限値の取り扱いに配慮。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - Z スコアをシグモイド変換して [0,1] にマッピングするユーティリティ実装（_sigmoid）。
    - ファクター重みの受け入れと検証（負値や非数値を除外、合計が 1.0 でない場合は再スケール）。
    - デフォルト重みおよび閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD = 0.60）。
    - AI レジームスコアの集計による Bear 判定（サンプル数閾値を適用して誤判定を抑制）。
    - BUY シグナル: final_score >= threshold（Bear レジーム時は BUY を抑制）。
    - SELL シグナル（エグジット判定）: ストップロス（-8%）およびスコア低下（final_score < threshold）。価格欠損時の判定スキップやログ出力を行う。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）。ROLLBACK 失敗時は警告ログ出力。

- strategy パッケージの __all__ に build_features / generate_signals を公開。

### Documentation / Design notes (コード内ドキュメント)
- 多数の関数・モジュールで設計方針・処理フロー・ルックアヘッドバイアス対策や冪等性・トランザクション戦略などをドキュメント化。
- エラーハンドリングやログ出力方針（warning/info/debug）を明確に記述。

### Security / Robustness
- defusedxml を用いた安全な XML パース（news_collector）。
- .env パーサーで予期しない行や無効行を無視する処理。
- API 呼び出しでのタイムアウト、再試行、トークン更新ロジックにより運用安定性を確保。
- DuckDB への書き込みにおいて PK 欠損行をスキップし、スキップ数を警告ログで報告。

### Known limitations / TODOs (ソース内記載)
- signal_generator の SELL 条件で未実装の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要なため未実装。
- 外部モジュール（例: kabusys.data.stats の実装自体は別ファイルで提供される想定）。
- 一部の振る舞い（例: news の銘柄紐付け、SSRF の完全対策）は設計方針として記載されているが実運用時の追加検証が必要。

### Breaking Changes
- 初版リリースのため該当なし。

---

参考:
- 各モジュールの docstring に設計方針・処理フローや制約が詳細に記載されています。導入・運用時は該当箇所（kabusys/config.py, data/jquants_client.py, data/news_collector.py, research/*, strategy/*）を参照してください。