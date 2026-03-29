CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はリリース日を示します。バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

フォーマット:
- Added: 新規追加機能
- Changed: 既存機能の変更・改善
- Fixed: バグ修正・回避策
- Removed / Security: 必要に応じて記載

Unreleased
----------
- なし（初回公開版に相当）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期公開
  - 基本パッケージエントリポイントとバージョンを追加（kabusys v0.1.0）。
  - パッケージ公開時に外部から利用可能なサブパッケージを __all__ で公開: data, strategy, execution, monitoring（パッケージ構成の意図を明示）。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする実装を追加。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、配布後も正しく .env を参照可能に。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化できるフラグを提供（テスト用途）。
  - 強力な .env パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメント等の取り扱い）。
  - settings オブジェクトを提供し、必須変数の取得（_require）や値検証（KABUSYS_ENV, LOG_LEVEL）を組み込み。
  - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）を提供。
- データ基盤（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar がない場合の曜日ベースフォールバック、DB登録値優先の一貫した挙動。
    - calendar_update_job により J-Quants から差分取得して idempotent に保存するバッチ処理を実装（バックフィル・健全性チェックあり）。
  - pipeline: ETL 処理用インターフェースと ETLResult データ構造を追加。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計。
    - ETLResult に実行結果、品質問題、エラー情報の集約と to_dict 出力機能を提供。
  - etl モジュールで ETLResult を再公開。
- 研究/分析機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する関数を実装。データ不足時の扱いを明示。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する関数を実装。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER、ROE を計算する関数を実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（fwd_1d, fwd_5d, fwd_21d等）を一括で取得する汎用実装を追加。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算する実装を追加。データ不足時の None 戻し。
    - rank: 同順位は平均ランクとするランク変換実装を追加（丸め誤差対策あり）。
    - factor_summary: 指定カラムについて count/mean/std/min/max/median を計算する統計サマリ機能を追加。
  - research パッケージの __all__ に主要関数を公開。
- ニュース NLP（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でバッチセンチメント評価して ai_scores に保存する機能を実装。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して厳密に集計。
    - 1 チャンク最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字でトリムするトークン肥大化対策。
    - JSON Mode を利用した出力期待と堅牢なバリデーション（JSON 抽出、results キー検査、コード照合、数値変換、クリッピング ±1.0）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数的バックオフで実施。失敗時は個別チャンクをスキップして処理継続（フェイルセーフ）。
    - DB 書込みは DELETE → INSERT のトランザクション（部分失敗時に既存スコアを保護）を実施。
    - ユニットテスト容易性のため _call_openai_api を差し替え可能（patch を想定）。
  - ai.regime_detector.score_regime:
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次の market_regime テーブルを更新する機能を実装。
    - マクロニュース抽出は定義済みキーワード群で raw_news をフィルタリング。
    - OpenAI 呼び出しは独立実装、リトライ・例外処理を備え、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジーム分類閾値（bull / neutral / bear）を定義し、冪等的な DB 書込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
- ロギング・安全策
  - 多数の関数でデバッグ / 警告 / 例外時のログメッセージを追加し、問題解析を支援。
  - DB 書込みでのトランザクション管理（COMMIT/ROLLBACK）を徹底し、ROLLBACK 失敗を警告ログで記録。
- テスト容易性
  - OpenAI API 呼び出し箇所に差し替えポイント（_call_openai_api）を用意し、ユニットテストでのモックを容易に。

Changed
- 初期実装段階なので既存バージョンからの破壊的変更はなし（初回リリース）。

Fixed
- 初回リリース：各モジュールで想定されるエラー条件（API 5xx / タイムアウト / JSON パース失敗 / DB 書込み失敗等）に対するフォールバックとログ出力を実装し、想定運用上の耐障害性を向上。

Notes / Design decisions
- ルックアヘッドバイアス防止:
  - score_news / score_regime 等の機能は内部で datetime.today() / date.today() を直接参照しない設計。必ず外部から target_date を与えることで過去データのみを参照するよう保証。
- DuckDB 互換性に関する注意:
  - executemany に空リストを渡さない対応（DuckDB 0.10 の制約）を実装。
  - 日付型の取り扱いに _to_date ユーティリティを使用して互換性を確保。
- 安全設計:
  - .env 読み込みでは OS 環境変数を保護する protected set を導入し、.env.local の override 振る舞いを安全に実装。
  - OpenAI API キー未設定時は ValueError を早期に発生させ、呼び出し側で明確に対処可能とする。

Acknowledgements / Future
- 将来的な改善候補（未対応・今後実装予定）
  - strategy / execution / monitoring の公開 API 実装（パッケージ構成上は存在を示すが本リリースでの詳細実装は限定的）。
  - PBR・配当利回りなどのバリューファクター拡張。
  - モデルやプロンプトのパラメータチューニング、バッチ最適化、コスト管理（OpenAI 呼び出しの効率化）。
  - より詳細な品質チェックルールの拡充（quality モジュールの拡張）。

以上。