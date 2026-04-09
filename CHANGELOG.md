# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-09

初回リリース。日本株の自動売買・リサーチ基盤として以下の主要機能を実装しました。

### Added
- パッケージ基盤
  - パッケージ名 kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パッケージ外部公開モジュール名として data, strategy, execution, monitoring を __all__ に宣言（将来的なモジュール追加のプレースホルダ）。

- 設定管理 / 環境変数読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - .env パーサーの実装（引用符、エスケープ、コメント、`export KEY=val` フォーマット対応）。
  - 環境変数保護（既存 OS 環境変数を protected として扱う上書き制御）。
  - Settings クラスを提供し、アプリケーションが利用する設定プロパティを整理：
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）/ PaperTrading 設定 / 監視閾値 / ログレベル / 環境（development/paper_trading/live）など。
  - 設定値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの有効値チェック）と未設定時の ValueError。

- AI ニュース解析（src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py）
  - raw_news + news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込むワークフローを実装。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と DuckDB を用いた記事集約。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）と 1 銘柄あたりの文字数・記事数制限（トークン肥大化対策）。
  - OpenAI 呼び出しに対するリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ実装。
  - レスポンスの厳密なバリデーション（JSON 抽出・results 配列確認・コード照合・数値検査）およびスコアの ±1.0 クリップ。
  - 部分失敗に対する DB 書き換え戦略（対象コードのみ DELETE → INSERT）により既存スコアの保護。
  - テスト用に OpenAI 呼び出し部分を差し替え可能（内部関数参照を想定）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM：重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
  - prices_daily のデータ取得でルックアヘッドを防止する設計（target_date 未満のみ参照）。
  - マクロニュース抽出キーワードセット実装および最大記事数制限。
  - OpenAI 呼び出しのリトライとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
  - トランザクション管理（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）とロギング。

- データプラットフォーム（src/kabusys/data/ 以下）
  - calendar_management.py
    - JPX マーケットカレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定 API を実装。
    - market_calendar がない場合は曜日ベース（土日非営業日）でフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント呼び出し、バックフィル、健全性チェック、冪等保存）。
  - etl.py / pipeline.py
    - ETL パイプライン用の公開インターフェースを提供（ETLResult の再エクスポート）。
    - ETLResult dataclass を実装し、ETL 実行時の取得数・保存数・品質問題・エラー情報を集約。has_errors / has_quality_errors プロパティと to_dict メソッドを提供。
    - pipeline の方針として差分更新・バックフィル（デフォルト 3 日）・品質チェックの集約を想定。

- 研究（research）モジュール（src/kabusys/research/ 以下）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）、バリュー（PER, ROE）などのファクター計算関数を実装。
    - DuckDB SQL とウィンドウ関数を活用して効率的に計算。データ不足時の None ハンドリング。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank（同順位平均ランク処理）、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ で便利関数群を再エクスポート。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 環境変数読み込みで OS 環境変数を protected として上書き保護する仕組みを導入（config）。

### Notes / Implementation details / 制約事項
- OpenAI API は gpt-4o-mini を使用する想定。API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要があります。未指定時は ValueError を送出します。
- DuckDB を主要なローカル DB として想定（prices_daily, raw_news, market_calendar, ai_scores, market_regime, raw_financials 等のテーブルを前提）。
- 日付ウィンドウ計算ではルックアヘッドバイアスを防ぐ設計を徹底（datetime.today()/date.today() を直接使わない実装方針）。
- API 呼び出し失敗時はフェイルセーフ（スコアを 0 にフォールバック、処理を継続）する方針を採用。
- 一部モジュール（例: data.jquants_client, data.quality, data.stats 等）は仕様を参照して呼び出されていますが、本リリースのコードベース内では外部クライアント実装や品質チェッククラスが実装済みであることを前提としています（別途実装が必要）。

今後の予定（例）
- strategy / execution / monitoring の実装（現在 __all__ に名前を公開済み）。
- テストカバレッジ向上、より詳細なログとメトリクス公開。
- OpenAI 呼び出しのコスト最適化・プロンプト改良。

-----
この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴やリリースノートは運用ポリシーに合わせて適宜調整してください。