CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-03
-------------------

初回リリース。日本株自動売買パイプラインのコア機能群を提供します。以下は実装済みの主な機能・設計方針の概要です。

Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__=0.1.0）。data / research / ai / monitoring / strategy / execution などのモジュールを公開対象に設定。

- 環境設定管理（kabusys.config）
  - .env ファイル自動読み込みを実装（プロジェクトルートの検出は .git または pyproject.toml を基準に探索）。
  - .env, .env.local の読み込み順・上書きルールを実装。OS環境変数を保護する仕組み（protected set）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - 独自の .env 行パーサ実装：export 句、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants／kabuステーション／LINE／DB／監視設定／システム設定等のプロパティを環境変数から取得。バリデーション（KABUSYS_ENV / LOG_LEVEL）とデフォルト値設定を含む。

- データ関連（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブルの利用）と夜間更新ジョブ（calendar_update_job）。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ日判定のユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが無い場合は曜日ベースのフォールバックを使用する設計。
    - 最大探索日数の上限やバックフィル・健全性チェック等の安全策を導入。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行の集計情報と品質問題・エラー一覧を格納）。
    - ETL パイプラインの設計（差分更新、バックフィル、品質チェックの収集、id_token 注入でのテスト容易化）に基づく実装方針を整理。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理（score_news）。
    - 設計上、前日15:00 JST～当日08:30 JST のウィンドウ定義（UTC変換）でルックアヘッドを防止。
    - バッチ処理（最大20銘柄/コール）、1銘柄あたりの記事・文字上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証（JSON整形・キー検査・型チェック）を実装。
    - API 失敗はフォールバック（該当チャンクはスキップ）し、全体の堅牢性を維持。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で部分失敗時に既存スコアを保護。DuckDB executemany の空リスト制約に配慮。
    - テスト容易性のため API 呼び出し関数をパッチ可能に設計。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出（score_regime）。
    - prices_daily から ma200 乖離を算出、raw_news からマクロキーワードで記事抽出、LLM（gpt-4o-mini）でマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ挙動。
    - LLM 呼び出しもパッチ可能に設計。

- リサーチ / 解析（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン・200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクターを DuckDB 上で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返すやり方で堅牢に実装。
    - 本モジュールは prices_daily / raw_financials のみ参照し、本番発注 API 等にはアクセスしないことを明示。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。Rank は平均ランク（同順位は平均）を採用。
    - 入力検証（horizons の制約等）と NaN/無限値の扱いを明示。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数で上書き可能かつ環境変数 OPENAI_API_KEY を参照する仕様。未設定時は明示的に ValueError を発生させ早期検出する。

Notes / Implementation details（重要な設計上の注意）
- ルックアヘッドバイアス対策:
  - news_nlp と regime_detector の両方で内部実装が datetime.today() / date.today() を用いない設計（外部から target_date を受け取る）となっており、将来データ参照を防止。
- トランザクションとエラーハンドリング:
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT 構成で冪等性を確保。失敗時は ROLLBACK を試行し、さらに ROLLBACK 自体の失敗をログ出力している。
- テスト支援:
  - OpenAI 呼び出し等、外部依存箇所は専用関数として切り出し（テストで patch 可能）している。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン対策（事前に空リストチェックを行う）。

既知の制約 / TODO（今後の改善余地）
- 一部の機能（監視モジュール monitoring, strategy, execution）の実装は公開インターフェースには含まれているが、今回のコードスナップショットでは全実装が確認できない箇所がある（将来追加予定）。
- PBR・配当利回りなどのバリューファクターは未実装。
- OpenAI レスポンスのフォールバックロジックは安全策を優先しており、失敗時の再取得戦略や詳細なログ収集の強化は今後の改善ポイント。

作者・貢献
- このリリースはコードベースから推測して CHANGELOG を作成しています。実際のコミット履歴やリリースノートはバージョン管理履歴にしたがって更新してください。

-----