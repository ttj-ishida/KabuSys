Keep a Changelog 準拠の形式で、このコードベースに基づく変更履歴を日本語で作成しました。
バージョンはパッケージ定義 (kabusys.__version__ == "0.1.0") に合わせて初回リリース 0.1.0 としています。

CHANGELOG.md
=============

すべての変更は SemVer に従います。  
詳細は https://keepachangelog.com/ja/1.0.0/ を参照してください。

Unreleased
----------

(現在なし)

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開用のトップレベル定義を追加（src/kabusys/__init__.py）。
  - モジュール公開リスト: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出し、CWD に依存しない読み込み。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）と、「保護済みキー」を考慮した上書きロジックを実装。
  - 行パーサーで export 形式、クォート・エスケープ、インラインコメント等に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、必須項目取得時は未設定で ValueError を送出するプロパティを整備。
  - 主要設定項目の既定値（KABUSYS_ENV, LOG_LEVEL, KABUS_API_BASE_URL, DB パス等）を定義。

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメント スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) にバッチ送信して銘柄ごとのセンチメントを ai_scores に保存するワークフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数のトリム、JSON Mode 応答のバリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを避ける設計（date 引数ベース、today() を直接参照しない）。
    - OpenAI 呼び出しロジックは news_nlp とは独立（モジュール結合を低減）。

- データ処理・ETL (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を参照した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day のロジックを提供。
    - market_calendar が未取得の際は曜日（平日/週末）ベースでフォールバックする一貫した動作。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存する処理を実装（バックフィルと健全性チェックを含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し etl モジュールとして再エクスポート（src/kabusys/data/etl.py）。
    - 差分取得、バックフィル、品質チェック結果の収集、保存処理（DuckDB）を想定したユーティリティ実装。
    - DuckDB の互換性（executemany の空リスト回避や型変換）を考慮した実装方針。
  - jquants_client 連携（モジュール参照場所を確保、calendar 更新等で利用）を想定。

- 研究（Research）ユーティリティ (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR, relative ATR）、Value（PER/ROE）の計算関数を実装。
    - DuckDB を用いた SQL ベースの集計で、過不足データ時に None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - forward returns（fwd_1d, fwd_5d, fwd_21d 等）を複数ホライズンで一括取得する calc_forward_returns を実装。
    - Spearman ランク相関（IC）を計算する calc_ic、ランク化ユーティリティ rank、統計サマリを行う factor_summary を実装。
  - 研究用 API を __all__ で公開（zscore_normalize は data.stats から再利用）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の重要事項
- OpenAI API
  - news_nlp と regime_detector は OpenAI (gpt-4o-mini) を利用する想定。api_key は関数引数で注入可能（api_key 引数優先）、未指定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を発生させる。
  - テストしやすいように _call_openai_api をモック可能に設計している。
  - API 呼び出し失敗時は多くのケースで例外を投げずフェイルセーフ（0.0 やスキップ）して継続する設計。
- ルックアヘッドバイアス対策
  - AI やファクター計算は内部で datetime.today()/date.today() を直接参照せず、明示的な target_date 引数を用いることで将来情報の参照を防止している。
- 環境変数 / 自動読み込み
  - Settings により JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須変数を管理。自動 .env 読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- DB（DuckDB）
  - 多くのデータ処理は DuckDB 接続を想定。executemany の空リスト問題など、DuckDB のバージョン互換性を考慮している。
- ロギング
  - 各モジュールで logger を利用し、警告や情報ログで異常系を明記している（例: データ不足、API パース失敗、ROLLBACK 失敗など）。

互換性 / マイグレーション
- 初回リリースのため後方互換性の変更点はなし。
- Settings の必須環境変数が未設定の場合、多くの機能が ValueError を発生させるため、導入時は .env もしくは OS 環境に必要なキーを設定してください。
  - 主要なキー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY

開発者向け備考
- 単体テストは OpenAI 呼び出しをモックすることを想定（_call_openai_api を差し替え）。
- .env のパースはエスケープやクォート処理に対応しているため、複雑な値も扱えるが特殊ケースは追加テスト推奨。

---
（以上）