CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
安定版のみを semver（MAJOR.MINOR.PATCH）で管理します。

[Unreleased]
-------------

（現時点のリリースはありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - 公開サブパッケージ: data, strategy, execution, monitoring。
- 環境/設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装（.env, .env.local の優先順）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサー実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメント処理などを考慮）。
    - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等のプロパティを提供。
    - env 値と log_level のバリデーションを実装（許容値チェック）。
    - 必須環境変数未設定時に ValueError を送出する _require 関数を提供。
- AI モジュール:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント分析し、ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - 記事の集約（news_symbols 結合）、チャンクバッチ処理（最大 20 銘柄/回）、1銘柄あたりの記事/文字数上限トリムを実装。
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーションと JSON 抽出（余分な前後テキストへのフォールバック）を実装。
    - スコアの ±1.0 クリップ、部分成功時に既存データを破壊しない（対象コードのみ DELETE → INSERT）書き込みを実装。
    - テスト容易性のため _call_openai_api をラップしパッチ可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - prices_daily / raw_news を DuckDB から安全に参照（ルックアヘッド回避のため target_date 未満条件など）。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行、フェイルセーフ（API 失敗時 macro_sentiment = 0.0）を実装。
    - レジーム算出後は冪等に DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - テスト容易性のため news_nlp と呼び出し実装を分離（モジュール結合を避ける）。
- データプラットフォーム関連:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の読み書き、営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が空のときは曜日ベース（週末除外）でフォールバックするロジックを採用。
    - next/prev/get_trading_days の最大探索日数上限を導入して無限ループを防止。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得 → 保存を行うフローを提供（バックフィル・健全性チェックあり）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤を実装（差分取得、保存、品質チェックの概念を実装）。
    - ETLResult データクラスを実装し、処理結果・品質問題・エラーを集約して to_dict でダンプ可能に。
    - DuckDB 上の最大日付取得などのユーティリティを提供。
  - src/kabusys/data/etl.py
    - パブリックインターフェースとして ETLResult を再エクスポート。
  - data パッケージ基盤（jquants_client, quality など外部クライアントを想定）。
- Research モジュール:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）・200日 MA 乖離、ATR（20日）・相対 ATR、平均売買代金・出来高比率、バリュー（PER・ROE）等のファクター計算ロジックを実装。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す堅牢な実装。
    - 実行は prices_daily/raw_financials のみ参照、外部 API には影響しない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（可変ホライズン対応、入力検証含む）。
    - ランク相関（Spearman）による IC 計算 calc_ic、rank ユーティリティ。
    - ファクター統計サマリー factor_summary。
    - 標準ライブラリのみでの実装を徹底し、pandas 等に依存しない設計。
- 公開 API/ユーティリティ:
  - src/kabusys/ai/__init__.py および src/kabusys/research/__init__.py で主要関数を再エクスポート。
  - テストを想定した設計（OpenAI 呼び出しのラッピング、環境ロード無効化フラグ等）。

Changed
- （初期リリースのため該当なし）

Fixed
- DuckDB の executemany に関する互換性配慮:
  - ai_scores 書き込み前に params が空でないことを確認してから executemany を呼ぶ（DuckDB 0.10 の制約を考慮）。
- OpenAI API レスポンスパースの堅牢化:
  - JSON mode でも前後に余分なテキストが混入するケースに備え、最外周の {} を抽出してパースするフォールバックを導入。
- ルックアヘッドバイアス対策:
  - 各日次/ニュース/レジーム判定処理は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計で実装。

Security
- 機密情報管理:
  - .env 自動読み込み時に既存 OS 環境変数を保護する protected キーセットを導入（.env.local の override 挙動も考慮）。

Known issues / Limitations
- news_nlp: 現バージョンでは sentiment_score と ai_score を同値で保存。将来的に別計算が想定される。
- factor_research: PBR・配当利回りなど一部バリューファクターは未実装（注記あり）。
- 設定・外部クライアント:
  - J-Quants / kabu / Slack / OpenAI の実際のクライアント実装（jquants_client など）は別モジュールに依存する想定で、外部 API の詳細実装は本リリース外の箇所がある可能性あり。
- OpenAI API 依存:
  - gpt-4o-mini の使用を前提としており、API 仕様変更に備えたエラーハンドリングは実装されているが、将来的な SDK 変更による追加対応が必要になり得る。

Notes for maintainers
- テスト容易性のため、OpenAI 呼び出しや自動 .env ロードを簡単に差し替え・無効化できる設計になっています。ユニットテストではこれらをモック/パッチしてください。
- DuckDB に対する SQL は互換性を考慮していますが、バージョン差異（特に配列バインドや executemany の挙動）に注意してください。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は、差分コミット・PR の説明や実際の動作検証に基づいて文言を調整してください。