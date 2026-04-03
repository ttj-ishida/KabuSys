# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

注: 以下の変更履歴は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-03

Added
- パッケージの初期リリースとして主要機能群を実装。
- 基本パッケージ情報
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - src/kabusys/__init__.py でモジュール公開: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を読み込み（OS 環境変数優先、.env.local は上書き）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須値取得用の _require、環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等）、デフォルトパス（DuckDB / SQLite / PID / kill flag）を提供。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信し、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／リクエスト）、1 銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を用いた厳密なレスポンス期待、レスポンスパースの耐性（前後の余計なテキスト抽出）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ。非再試行エラーは安全にスキップ。
    - スコアは ±1.0 にクリップ。部分成功に備え、書き込み時は対象コードのみを削除→挿入（冪等・部分失敗保護）。
    - テスト用に内部の API 呼び出し関数を差し替え可能（unittest.mock.patch 想定）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF コード 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離 (_MA_WINDOW=200) とマクロニュースの LLM センチメントを合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200 の重み 70%、マクロセンチメントの重み 30% で合成。閾値に基づきラベル付け。
    - raw_news からマクロキーワードで記事を抽出、最大件数制限、記事がない場合は LLM 呼び出しをスキップしてフェイルセーフ（macro_sentiment=0.0）。
    - OpenAI 呼び出しはリトライ/バックオフ/エラーハンドリングを実装。DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理、エラー時は ROLLBACK を試行。

- データプラットフォーム (src/kabusys/data/)
  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得件数、保存件数、品質検査結果、エラー一覧など）。
    - 差分更新、バックフィル日数、品質チェックのための設計方針やユーティリティ関数を実装（DuckDB を利用）。
    - jquants_client 経由での差分取得、保存処理（idempotent）等を想定。
    - DuckDB の互換性注意（executemany に空リスト渡し不可など）を考慮した実装。

  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定・隣接営業日探索機能を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新 job (calendar_update_job): J-Quants から差分取得→保存、バックフィル日数・健全性チェックを実装。
    - 探索の最大範囲制限 (_MAX_SEARCH_DAYS=60) により無限ループを防止。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）を計算。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグ処理を実装。
    - データ不足時の扱い（必要行数不足なら None を返す）やログ出力を明確化。

  - 特徴量探索 / 統計ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）。
    - IC（Information Coefficient）計算（スピアマンランク相関）とランク付けユーティリティ（rank）。
    - factor_summary による基本統計量（count, mean, std, min, max, median）算出。
    - 外部依存（pandas 等）を用いず、標準ライブラリ＋DuckDB で実装。

- 汎用 / エクスポート
  - ai/__init__.py と research/__init__.py による主要関数の再エクスポート（score_news、研究用関数群など）。
  - 設計メモ・ドキュメント（モジュール docstring）でルックアヘッドバイアス回避方針やフェイルセーフ戦略を明示。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境ファイルパーサーの強化（src/kabusys/config.py）
  - export KEY=val 形式の許容、シングル/ダブルクォート内のバックスラッシュエスケープ正処理、インラインコメント扱いの改善。
  - プロジェクトルート探索は __file__ を起点に上位ディレクトリを探索する実装とし、CWD に依存しない挙動に。

Security
- （初回リリースのため該当なし）

Notes / 既知の設計判断（重要）
- OpenAI API の利用
  - gpt-4o-mini を想定し JSON モードを利用する設計。API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。
  - API 呼び出し失敗時は多くのケースでフォールバック（スコア 0.0 の採用や当該チャンクスキップ）することで、ETL/判定ジョブ全体が停止しないようにしている。
  - テスト容易性のため、内部の API 呼び出し関数をモック差し替えできる設計。

- データベース書き込みの冪等性
  - market_regime / ai_scores 等への書き込みは既存行を削除して再挿入する方式を採用し、部分失敗時に他コードの既存スコアを消さないなどの配慮をしている。
  - トランザクション管理（BEGIN/COMMIT/ROLLBACK）と例外時のログを実装。

- ルックアヘッドバイアス対策
  - すべての分析/スコアリング関数は内部で datetime.today()/date.today() を無闇に参照せず、target_date を必須引数として外部から与える形を採用。

- DuckDB 互換性注意
  - executemany に空リストを渡すと失敗するバージョンを考慮して、空チェックを入れている。

今後の TODO（推定）
- strategy / execution / monitoring パッケージの具体的な実装（__all__ に宣言されているが詳細は未提示）。
- より詳細なテストと CI（特に OpenAI 呼び出し箇所のモックによる単体テスト）。
- ドキュメント整備（Usage examples、環境変数の .env.example など）。

---

参照: 本 CHANGELOG は提供されたソースコードの内容と docstring から推測して作成しています。実際のコミット履歴に基づくものではありません。