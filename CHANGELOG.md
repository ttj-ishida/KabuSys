# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従っています。  

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムの基盤機能（データ取得/処理、リサーチ、AI ベースのニュース解析・レジーム判定、カレンダー管理、ETL ユーティリティ、設定管理）を提供します。

### Added
- パッケージ基盤
  - パッケージ定義とバージョン情報を追加（kabusys v0.1.0）。
  - public API エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイル(.env, .env.local) および OS 環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export 文対応、シングル/ダブルクォートのエスケープ、インラインコメント処理）。
  - 読み込み時の上書き制御（override）と保護キー（protected）をサポートし、OS 環境変数の保護を実現。
  - Settings クラスを提供し、以下の設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live/is_paper/is_dev

- AI モジュール
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ書き込む score_news を実装。
    - 時間ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に相当する UTC 範囲）。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの最大記事数・文字数トリム、JSON Mode を用いた厳格なレスポンス検証。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API エラー時にはスキップして継続するフェイルセーフ。
    - レスポンス検証とスコアクリッピング（±1.0）、部分成功時の DB 書き換えは対象コードだけを削除→挿入することで既存データを保護。
    - テスト容易性のため _call_openai_api をモック可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロニュース抽出はマクロキーワードリストによるフィルタリング。LLM 呼び出しは gpt-4o-mini を使用し、JSON のみを期待。
    - リトライ、エラー時のフォールバック（macro_sentiment=0.0）、レスポンスパース失敗時の警告ログ。DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テストで差し替え可能な _call_openai_api を用意。

- リサーチ（src/kabusys/research/*）
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200 日 MA に対する乖離）の算出。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) の算出。
    - calc_value: EPS/ROE から PER と ROE を計算（raw_financials と prices_daily を使用）。
    - いずれも DuckDB 上の SQL＋Python で実装、データ不足時の None ハンドリング。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を利用）、horizons 引数検証。
    - calc_ic: ランク相関（Spearman の ρ）による IC 算出、サンプル数不足時は None。
    - rank: 同順位は平均ランクを採る実装（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。

- データ基盤（src/kabusys/data/*）
  - calendar_management
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得時の曜日ベースフォールバックを提供。探索上限（_MAX_SEARCH_DAYS）や健全性チェックを実装。
    - calendar_update_job: J-Quants からカレンダーデータを差分取得し保存する夜間バッチジョブを実装。バックフィルと sanity check をサポート。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）。
    - ETL パイプラインの骨格（差分取得、保存、品質チェックの統合方針）を実装。DuckDB の最大日付取得ユーティリティ等を提供。
  - jquants_client と quality などの外部クライアント/モジュールと連携するためのフックを用意（実際の fetch/save は jquants_client 側に委譲）。

- テスト・運用配慮
  - LLM 呼び出し部分（news_nlp/regime_detector）の _call_openai_api をモック容易に設計。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（全関数は target_date を引数に受けるか、明示的に今日を取得する場所を限定）。
  - DuckDB バインドの互換性対策（executemany に空リストを渡さない等の防御実装）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報は環境変数から取得する設計（API キーやパスワードは Settings を通じて参照）。OpenAI API キー未設定時は明示的に ValueError を投げることで誤用を防止。

### Notes / Important usage
- OpenAI API
  - score_news / score_regime は OpenAI API（gpt-4o-mini）を使います。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定の場合は ValueError を送出します。
  - レスポンスは JSON mode を期待し、パース失敗や API エラーは基本的にフェイルセーフで代替値（例: macro_sentiment=0.0）を使用します。

- データベースとスキーマ依存
  - 多くの関数は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）を前提とします。これらのスキーマが存在しない場合は機能しません。
  - ai_scores / market_regime 等への書き込みは冪等化を意識した実装になっていますが、初期データモデルの整備が必要です。

- ロギング
  - 各モジュールは logger を使用して情報・警告・エラーを出力します。LOG_LEVEL による制御が可能です。

### Known issues / Limitations
- 外部 API（J-Quants, OpenAI）依存のため、API のレート制限やスキーマ変更が発生した場合の影響は残ります。リトライやバックオフを入れているものの、部分失敗はあり得ます。
- news_nlp の JSON パース回復処理は「最外の {} を抽出」する戦術的な実装に依存しており、LLM 出力の大幅な逸脱には脆弱です。
- calc_value は現時点で PBR・配当利回りを未実装。

---

（補足）ドキュメントや運用手順、CI テスト、サンプル DB スキーマは別途整備を推奨します。