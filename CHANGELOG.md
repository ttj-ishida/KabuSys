# CHANGELOG

すべての主な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

- リリース日付はコードベースから推測して記載しています。
- 記載内容はソースコード（src/ 以下）を参照して機能・設計方針・制約を推定したものです。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys
  - パッケージメタ情報（src/kabusys/__init__.py: __version__ = "0.1.0"）を追加。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）または環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基に探索（CWD に依存しない）。
  - .env のパースはコメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどを考慮した堅牢な実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で使用可能）。
  - Settings クラスを提供（settings インスタンスをエクスポート）。以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
    - ヘルパー: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄毎のニュースを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で計算）。
    - バッチ処理: 1 API コールで最大 20 銘柄ずつ処理、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - 再試行: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ）。
    - レスポンス検証機能を実装（JSON 抽出、"results" リスト検証、code と score の型検査、スコアの ±1.0 クリップ）。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガード。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト容易化のため内部の OpenAI 呼び出しを差し替え可能に設計（_call_openai_api のモック）。

  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の算出は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュースは news_nlp の calc_news_window を使ってウィンドウを算出し、タイトルベースでマクロキーワード検索を実行。
    - OpenAI 呼び出しは独自実装で行い、失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- Data モジュール（src/kabusys/data）
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日ロジックを実装。
    - market_calendar が存在しない場合は曜日ベース（平日のみ営業）でフォールバック。DB 登録がある場合は DB 値を優先、未登録日は曜日フォールバックで一貫した判定を提供。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等保存（バックフィル、健全性チェック含む）。
    - 最大探索範囲やバックフィル日数等、実運用を想定した安全策を組み込み。

  - pipeline / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL のための ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラー等を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュール使用想定）を行う設計を反映。
    - jquants_client との連携を前提とした保存ロジック（Idempotent）を想定。
    - data.etl は ETLResult を再エクスポート。

- Research モジュール（src/kabusys/research）
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算する calc_momentum を実装。
    - ボラティリティ・流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。
    - バリュー: raw_financials から最新財務（EPS, ROE）を取得して PER / ROE を計算する calc_value を実装。
    - DuckDB の SQL ウィンドウ関数と Python の組合せで実装し、外部 API には依存しない。

  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（デフォルト horizons=[1,5,21]）。
    - IC 計算（Spearman ρ）: calc_ic（ランク化して相関算出、十分なデータが無ければ None）。
    - ランク関数: rank（同位値は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - pandas 等の外部ライブラリに依存せず純標準ライブラリで実装。

- その他
  - DuckDB を主要なデータストアとして利用する前提で実装（関数引数に DuckDB 接続を受け取る）。
  - OpenAI のレスポンスを JSON Mode（response_format={"type": "json_object"}）で受け取り、パース／検証する設計。
  - 主要な設計方針をコード内ドキュメントに明記（ルックアヘッドバイアス回避、フェイルセーフ、モジュール結合回避、DuckDB 互換性考慮 等）。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Known limitations / Notes
- DuckDB バインドの挙動依存: executemany に空リストを与えるとエラーになるバージョン（例: DuckDB 0.10）を考慮した防御が入っているため、利用する DuckDB バージョンによっては細かい挙動差がある。
- OpenAI 依存: gpt-4o-mini を想定。API レスポンスの形式や SDK の変化（例: status_code の有無）に対して耐性を持つ実装だが、将来の互換性変更に注意が必要。
- 時刻処理: ニュースウィンドウ等は UTC-naive な datetime を使っており、JST ↔ UTC の変換をコード内で明示している。タイムゾーンを跨ぐ運用時は注意。
- 一部設計（品質チェックモジュール quality、jquants_client の実装）はソースに参照はあるが本体実装は別モジュールを想定しているため、実運用にはそれらの実装が必要。
- テスト容易化のため、内部の OpenAI 呼び出しポイントをモック可能に設計している（unittest.mock.patch で差し替え可能）。

---

以上が、ソースコードの内容から推測して作成した CHANGELOG（Keep a Changelog 準拠）です。必要ならばリリース日や細部表現の修正、各機能ごとの Breaking changes 追記なども対応します。