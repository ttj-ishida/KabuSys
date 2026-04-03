CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルは人間と自動化ツールの両方で参照できるように英語ではなく日本語で記載しています。

フォーマット:
- Unreleased: 未リリースの作業（今後の変更）
- 各バージョンごとに Added / Changed / Fixed / Removed / Security 等で分類

[Unreleased]
------------

- なし（初回リリース後の未反映項目はここに記載します）

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期公開: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__=0.1.0、主要サブパッケージを __all__ で公開）
- 環境設定管理
  - robust な .env 自動読み込み機構を実装（src/kabusys/config.py）
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）
    - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）
    - export KEY=val 形式やクォート内のエスケープ処理、行末コメントの扱いに対応するパーサを実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能
  - Settings クラスを提供し、各種設定値（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル 等）の取得とバリデーションを実装
    - 必須キー未設定時は明示的な ValueError を送出
    - KABUSYS_ENV の値検証（development / paper_trading / live）
    - デフォルト DB パス、PID/kill flag 等の既定値設定

- AI モジュール（OpenAI 統合）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成
    - gpt-4o-mini（JSON Mode）へバッチ送信（最大20銘柄/チャンク）
    - レスポンスの厳密バリデーション（JSON 抽出、results キー、code/score の型チェック）
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - エラー時は個別チャンクをスキップするフェイルセーフ設計（リトライ・指数バックオフ対応）
    - DuckDB の executemany 空リスト制約への回避（empty params を送らない）
    - calc_news_window ユーティリティ（JST ウィンドウから UTC naive datetime を生成）
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200日 MA 乖離（70%）とマクロセンチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）
    - マクロニュースは news_nlp の calc_news_window によるウィンドウで抽出
    - OpenAI 呼び出しをモジュール内で独立実装し、news_nlp と内部関数を共有しない設計（モジュール結合を低減）
    - API リトライ（429/ネットワーク断/タイムアウト/5xx）とフォールバック（マクロセンチメント失敗時は 0.0）
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）, 失敗時は ROLLBACK を試行して例外を上位へ伝播
    - lookahead バイアス防止（target_date 未満のみ参照、datetime.today() を参照しない）

- Research（因子・特徴探索）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）等の計算関数を提供
    - DuckDB のウィンドウ関数を活用し営業日ベースでの計算を実装
    - データ不足時は None を返す仕様
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（horizons デフォルト [1,5,21]、horizons の検証）
    - Spearman（ランク）ベースの IC 計算（calc_ic）
    - ランク変換（平均ランク、同順位は平均）
    - factor_summary による基本統計量（count/mean/std/min/max/median）
    - pandas 等に依存しない実装（標準ライブラリのみ）
  - research パッケージの再エクスポート（zscore_normalize の re-export 等）

- Data（ETL / カレンダー / パイプライン）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定・next/prev/get_trading_days/is_sq_day を実装
    - DB に値がない場合は曜日ベースでフォールバック（週末を非営業日扱い）
    - calendar_update_job による J-Quants 差分取得／冪等保存（バックフィル・健全性チェック搭載）
    - 最大探索日数やバックフィル日数等の保護ロジックを実装
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を導入（取得/保存レコード数、品質問題、エラー一覧を保持）
    - 差分取得、保存、品質チェックの流れに合わせた設計（backfill, calendar lookahead 等）
    - DuckDB 存在チェックユーティリティ等を実装
  - ETL の公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート
  - jquants_client を想定した外部クライアント呼び出し箇所を用意（モジュール間インターフェース設計）

- インフラ / 運用
  - デフォルトのファイルパス設定（DuckDB, SQLite, PID/kill flag 等）を Settings で提供
  - 監視用閾値（CPU/MEM/DISK）や kill flag のクリアオプションなどの運用機能を環境変数で制御可能

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Known limitations / Notes
- OpenAI API を使用するため、OPENAI_API_KEY（もしくは関数引数での注入）が必須。未設定時は ValueError が発生する。
- ニュース NLP / レジーム判定は LLM レスポンスに依存するため、レスポンスフォーマットの変化に対して脆弱性が残るが、JSON 抽出やレスポンスバリデーションである程度の回復性を持たせている。
- raw_financials からのバリュー指標は現時点で PER / ROE のみを提供。PBR や配当利回りは未実装。
- DuckDB バージョン差異（executemany の空リスト等）を回避する互換コードを導入しているが、将来の DuckDB 仕様変更に注意。
- calendar_update_job は jquants_client を使用するため、外部 API の可用性に依存する。API エラー時は安全に 0 を返す（処理継続）。

Dependencies / Requirements
- DuckDB（DuckDB 接続を受け取る設計）
- openai Python SDK（OpenAI の Chat Completions を利用）
- J-Quants / kabu API など外部データソースとの連携を想定

開発上の設計方針（抜粋）
- ルックアヘッドバイアス回避: datetime.today()/date.today() を内部ロジックで不用意に参照せず、必ず target_date を外部から注入する設計。
- フェイルセーフ: 外部 API（OpenAI/J-Quants 等）の失敗は局所的にフォールバック（0.0 やスキップ）して全体の処理を停止させない。
- 冪等性: DB 書き込みは部分失敗時にも既存データを毀損しないように設計（DELETE → INSERT、code を絞る等）。
- テスト容易性: API 呼び出し関数はモジュール内で独立実装しパッチ可能にしてユニットテストを容易化。

最初のリリースに関する補足
- 本バージョンはコア機能（データ取得・ETL の構成要素、因子計算、ニュース NLP、レジーム判定、カレンダー管理、設定管理）を実装した初期版です。これらを組み合わせて日本株の自動売買・リサーチ基盤の基礎を提供します。今後は strategy / execution / monitoring パッケージの具現化、テストカバレッジ拡充、運用向けの堅牢化を進める予定です。