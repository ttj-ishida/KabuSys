KEEP A CHANGELOG 準拠の CHANGELOG.md（日本語）

すべての変更は https://keepachangelog.com/ja/ の慣例に従って記載しています。

## [0.1.0] - 2026-04-04

リリース初版。パッケージ名: kabusys - 日本株自動売買／データプラットフォーム向けユーティリティ群の最小実装を提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。公開サブパッケージを __all__ で定義。

- 環境設定 / 設定管理
  - kabusys.config.Settings: 環境変数ベースの設定取得クラスを追加。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - .env ファイルのパース（コメント、export 句、シングル/ダブルクォート、エスケープ）に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須設定取得用の _require ヘルパー、ログレベル・環境種別の検証（有効値集合）を実装。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、閾値等。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp.score_news
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) により銘柄別センチメントを算出し ai_scores に書き込むスコアリング処理を実装。
    - バッチ処理（最大20銘柄/チャンク）、文章トリム、JSON Mode の応答パース、レスポンス検証を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - 書き込みは部分失敗を考慮した DELETE→INSERT の置換方式で冪等性を確保。
    - calc_news_window: JSTベースのニュース収集ウィンドウ計算を実装（前日15:00〜当日08:30 JST を UTC で扱う）。

  - kabusys.ai.regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ書き込む処理を実装。
    - マクロニュース抽出（キーワードベース、最大記事件数制限） → OpenAI による JSON 出力パース → スコア合成。
    - OpenAI 呼び出しのリトライ、API 障害時のフォールバック（macro_sentiment=0.0）を実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ハンドリングで冪等性を確保。

- データプラットフォーム（Data）モジュール
  - kabusys.data.calendar_management
    - market_calendar を用いた営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にカレンダーがない場合は曜日ベース（土日）でフォールバックするロジックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間ジョブを実装。バックフィル・健全性チェックを含む。
    - 最大探索日数、バックフィル日数、先読み日数等の定数を公開。

  - kabusys.data.pipeline / ETL
    - ETLResult データクラスを追加（ETL 実行結果の集約、品質チェック問題およびエラーの保持）。to_dict メソッドでシリアライズ可能。
    - パイプラインユーティリティ（差分取得・品質チェック・保存の方針）用の基盤実装と補助関数を追加（テーブル存在チェック、最大日付取得などのユーティリティを含む）。
    - kabusys.data.etl で ETLResult を再エクスポート。

  - jquants_client への依存を前提とした設計（fetch/save 関数を想定、calendar_update_job 等で使用）。

- 研究（Research）モジュール
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を計算する関数を実装（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などを計算する関数を実装。
    - calc_value: raw_financials から EPS / ROE を取得し PER/ROE を計算する関数を実装（最新報告日以前のデータを取得）。
    - 各関数は date, code をキーとする dict のリストを返す仕様。

  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 平均ランク処理（同順位は平均ランク）を実装。丸めを行い ties 検出の安定化を図る。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出するユーティリティを追加。

- ロギングおよび設計方針に関する注記
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（外部から target_date を渡す）。
  - DuckDB を主要なローカルデータベースとして利用。
  - OpenAI 呼び出し箇所はテスト時に差し替え可能（内部 _call_openai_api を patch でモック可能）。
  - API 呼び出し失敗時は例外直上げではなくフェイルセーフ動作（0.0 / スキップ）を採用する箇所がある。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 破壊的変更 (Removed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キー等の機密設定は環境変数経由で取り扱う設計。.env 読み込みでは OS 環境変数を保護するための protected キー集合を使用。

### 既知の制限・注意点 (Known issues / Notes)
- news_nlp の出力スキーマは LLM に依存するため、まれに余計な前後テキストが混入することがある。その場合は最外の {} を抽出して復元するロジックを組み込んでいるが、必ず成功するわけではない。
- calc_value では現時点で PBR・配当利回りは未実装（将来の拡張候補）。
- DuckDB バージョンや SQL バインディング側の挙動によっては executemany の空リスト渡しが非互換なため、空チェックを入れている。
- OpenAI のモデルとして gpt-4o-mini を指定している。API バージョン差異によりエラー型や status_code の有無が変わる可能性があるため、コード中で安全に属性を参照する実装をしている。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar の実装に依存する。

---

開発・運用に関する詳細（API 仕様、DB テーブル定義、運用手順）はリポジトリ内の Research / Data / Strategy ドキュメント（別途整備）を参照してください。