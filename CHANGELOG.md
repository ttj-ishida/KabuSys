Keep a Changelog
すべての重要な変更はこのファイルに記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- （なし）

[0.1.0] - 2026-03-31
Added
- 初回リリースとして kabusys パッケージを追加。
  - パッケージ公開 API (src/kabusys/__init__.py): __version__ = "0.1.0"、主要サブパッケージを __all__ で宣言（"data", "strategy", "execution", "monitoring"）。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出機能: .git または pyproject.toml を探索して自動ロードの基準を決定。
  - .env パーサ: export 構文、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応する堅牢なパーシング実装。
  - 自動ロードの挙動: OS 環境変数を保護する protected 機能、.env と .env.local の優先度、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
  - Settings クラス: 必須トークン（JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や DB パス、KABUSYS_ENV / LOG_LEVEL の検証ロジックを提供。
- AI モジュール (src/kabusys/ai/)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news を用いたニュースセンチメント分析機能 score_news を実装。
    - タイムウィンドウ計算、銘柄ごとの記事集約、トークン肥大対策（記事・文字数のトリム）、バッチ（最大20銘柄）での OpenAI 呼び出し。
    - OpenAI 呼び出しに対する指数バックオフ・リトライ、レスポンスの JSON バリデーション、スコアのクリップ処理（±1.0）。
    - DuckDB への冪等書き込み（DELETE → INSERT）およびトランザクション処理を実装。
    - 単体テスト用に _call_openai_api をモック差し替え可能。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し、フェイルセーフ（API失敗時は macro_sentiment=0.0）、スコア合成と market_regime テーブルへの冪等書き込み。
    - OpenAI SDK の 5xx/ネットワーク系例外の取り扱いとリトライ処理を実装。
- Data モジュール (src/kabusys/data/)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー取得・管理と営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar がない場合は曜日ベース（週末は非営業日）でフォールバックする一貫した動作。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理。バックフィル・健全性チェックを実装。
  - etl / pipeline (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装（ETL の結果集約、品質問題・エラー収集、has_errors 等のユーティリティ）。
    - テーブル存在チェック、最大日付取得など ETL 実装に必要な内部ユーティリティを追加。
    - etl モジュールは pipeline.ETLResult を公開再エクスポート。
  - DuckDB を主要なローカルデータストアとして利用する設計（各モジュールで DuckDB 接続を受け取る）。
- Research モジュール (src/kabusys/research/)
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、出来高・売買代金指標等の計算関数 calc_momentum, calc_volatility, calc_value を実装。
    - DuckDB によるウィンドウ関数を活用した実装（営業日ベースの窓、データ不足時の None 扱いなど）。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、Spearman による IC 計算 calc_ic、rank、factor_summary を実装。
    - pandas 等に依存しない標準ライブラリのみでの実装。
  - research パッケージの __init__.py で主要関数を再エクスポート。
- テスト・運用性向上
  - OpenAI 呼び出しの抽象化（各モジュールで _call_openai_api を定義）により単体テストでのモック差し替えを容易化。
  - DuckDB の executemany の挙動（空リスト不可）に配慮した実装（空チェックの明示）。
- ロギング・エラーハンドリング
  - 重要処理におけるログ出力を整備（info/debug/warning/exception）。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）を確実に行い、ROLLBACK 失敗時も警告ログを出す堅牢性を確保。

Changed
- 初回リリースのため履歴なし。

Fixed
- 初回リリースのため履歴なし（実装内でのフェイルセーフ・警告ログ等により実運用での問題を軽減）。

Security
- 環境変数ベースの機密情報管理を採用。必須項目（OpenAI API key, J-Quants token, kabu API パスワード, Slack トークン等）は Settings から取得し未設定時は ValueError を送出。
- .env 自動読み込みでは OS 環境変数を保護する設計（既存変数はデフォルトで上書きしない、.env.local は明示上書き可）。

Notes / Compatibility
- DuckDB を利用（DuckDB のバージョン差異に依存する箇所に注意。特に executemany の空リスト扱いなど互換性考慮済み）。
- OpenAI SDK を利用（model: gpt-4o-mini、response_format に JSON オブジェクト機能を使用）。SDK のエラー例外や属性（status_code 等）に対して互換性を考慮した実装を行っているが、将来の SDK 変更により挙動が変わる可能性あり。
- 時刻/日付の扱いはルックアヘッドバイアス防止の観点から date / naive UTC datetime を採用。target_date ベースで計算する仕様に注意。
- 一部モジュール（strategy, execution, monitoring）は __all__ に宣言されているが、今回のコードベースでは実装ファイルは含まれていません（将来的な追加を想定）。

作者注
- 各モジュールは「外部 API（取引 API 等）への直接発注を行わない」ことを設計方針としています。データ取得・特徴量計算・AI スコアリング・カレンダ管理を中核に据えたライブラリとして提供します。