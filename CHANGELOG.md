CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

----


0.1.0 - 2026-04-04
------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）
- コア構成・設定管理
  - 環境変数読み込みモジュール (kabusys.config)
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
    - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープを適切に処理
    - 上書き制御（override）と OS 環境変数を保護する protected セットの仕組みを実装
  - Settings クラスにより環境変数をプロパティとして公開（J-Quants, kabuステーション, LINE, DB パス, 監視閾値, ログレベル等）
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID/KILL フラグパス 等）を提供
    - is_live / is_paper / is_dev ヘルパーを提供

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini, JSON mode）へバッチ送信
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、エクスポネンシャルバックオフによるリトライ（429・ネットワーク断・タイムアウト・5xx）
    - レスポンスの厳密なバリデーション（JSON 抽出、"results" リスト、code の正規化、数値チェック）、スコアを ±1.0 にクリップ
    - DuckDB への書き込みは idempotent（対象コードに対して DELETE → INSERT）で部分失敗時に既存スコアを保護
    - テスト容易性のため _call_openai_api を patch 可能な設計
    - calc_news_window ユーティリティ（JST 時間ウィンドウを UTC naive datetime で返す）
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定
    - ma200_ratio 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを排除
    - マクロニュース抽出はキーワード群によるフィルタリング（最大 20 件）を実施し、記事がある場合のみ OpenAI に問い合わせ
    - OpenAI 呼び出しは JSON mode とし、リトライ/バックオフを実装。API 失敗時はフェイルセーフとして macro_sentiment=0.0 を使用
    - 計算結果は market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT）、DB 書き込みエラー時は ROLLBACK を試行

- データプラットフォーム関連（kabusys.data）
  - pipeline モジュールと ETLResult（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得・保存カウント、品質問題、エラー情報、has_errors/has_quality_errors、to_dict）
    - 差分更新、バックフィル、品質チェックを想定した ETL パイプライン設計（jquants_client および quality モジュールと連携）
    - テーブル存在確認や最大日付取得などのユーティリティ実装（DuckDB 前提）
  - calendar_management モジュール
    - market_calendar を基にした営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動
    - calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック（未来日付の過大な飛びを検出してスキップ）
    - データがまばらな場合でも一貫性を保つ設計（最大探索日数制限）

- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（データ不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播に配慮）
    - calc_value: PER / ROE を raw_financials と prices_daily を組み合わせて計算（EPS が 0/欠損時は None）
    - DuckDB のウィンドウ関数を活用し営業日ベースでの計算を実現
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用、ホライズン引数検証あり）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（ランク化ユーティリティを利用）
    - rank: 同順位は平均ランクで処理（round による ties 対応）
    - factor_summary: count/mean/std/min/max/median の基本統計量を純粋 Python で算出（None 除外）
  - kabusys.data.stats の zscore_normalize を再エクスポート（kabusys.research パッケージで利用可能）

- 汎用的な実装方針・品質
  - DuckDB をデータ層に採用（SQL + Python の混成で計算）
  - 外部 API 呼び出しに対する堅牢性（リトライ、バックオフ、レスポンス検証、フェイルセーフ）を重視
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を参照しない設計（target_date を明示的に引数化）
  - ロギングを各モジュールに導入し、重要な状態変化や警告を記録

Changed
- （初回リリースのため該当なし）

Fixed
- API 呼び出しやレスポンスパースの失敗時に例外を上位へ投げずフェイルセーフで処理を継続する挙動を多くの箇所で実装（AI モジュール、calendar_update_job 等）
- DuckDB の executemany が空リストを許容しない制約を考慮し、空チェックを行ってから executemany を呼ぶように実装（score_news 等）

Security
- 環境変数の必須チェックを導入（OpenAI API キー等）。未設定時は ValueError を送出して早期検出

Deprecated
- （初回リリースのため該当なし）

Notes / Migration
- OpenAI 利用には環境変数 OPENAI_API_KEY の設定が必要（score_news / score_regime の引数でも注入可能）
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に .env を利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や明示的に環境変数を設定してください

---- 

今後の予定（参考）
- モニタリング・実行モジュール（execution / monitoring）の具体的実装の追加
- jquants_client / quality モジュールの詳細実装と ETL の統合テスト
- 追加のファクター・戦略モジュールの追加とバックテストユーティリティの整備

---- 

（この CHANGELOG はリポジトリ内のコード構成とドキュメント文字列から推測して作成しています。実際のコミット履歴に基づくものではありません。）