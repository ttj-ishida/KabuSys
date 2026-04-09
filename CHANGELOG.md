CHANGELOG.md
=============

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

目次
----
- [0.1.0] - 2026-04-09

[0.1.0] - 2026-04-09
--------------------

Added
-----
- 初回リリース: kabusys パッケージ基盤を追加。
  - パッケージ公開バージョン: 0.1.0

- コア構成・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 読み込み時に既存 OS 環境変数を保護するため protected セットを使用して上書き制御を実装。
  - Settings クラスを実装し、アプリケーション設定をプロパティとして提供:
    - J-Quants / kabuステーション / LINE / DB パス（duckdb, sqlite, paper_trading） / PID/KILL フラグ / リソース閾値（CPU/メモリ/ディスク） / 実行環境（development, paper_trading, live） / ログレベル 検証付き。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）。
    - 環境変数未設定時は明確なエラーを投げる _require 関数を利用。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント分析 (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチでセンチメントを取得して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（JST 前日 15:00 〜 当日 08:30、UTC での前日 06:00 〜 23:30）を提供する calc_news_window を実装。
    - バッチサイズ、文字数制限、記事数制限などトークン肥大化対策を実装（_BATCH_SIZE, _MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。エラー時はフェイルセーフでスキップし処理を継続。
    - レスポンスの堅牢なバリデーションを実装（JSON 抽出、"results" 検証、code の正規化、数値チェック、±1.0 でクリップ）。
    - ai_scores への書き込みは部分成功に備え、書き換え対象コードを絞って DELETE → INSERT の冪等処理を行う。
    - エントリポイント: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しのリトライ／バックオフ、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - エントリポイント: score_regime(conn, target_date, api_key=None)

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にカレンダー情報がない場合は曜日ベース（土日休）でフォールバック。
    - next/prev_trading_day は最大探索日数制限で無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新する夜間バッチジョブを実装（バックフィル、健全性チェック含む）。
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL パイプラインのための ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー一覧等を集約）。
    - pipeline モジュールの型を etl から再エクスポート（ETLResult）。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - DuckDB SQL を中心にして外部 API に依存せず処理。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21）で将来リターンを計算（LEAD を使用して営業日ベース）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（少数レコードは None を返す）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties の扱いを工夫）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __all__ を整備して主要関数を公開。

Changed
-------
- 設計方針として各モジュールに共通の注意点を導入:
  - ルックアヘッドバイアスを避けるため datetime.today() / date.today() を直接参照しない設計（関数呼び出し側が target_date を渡す）。
  - DuckDB を想定した SQL 実装（互換性のため ROW_NUMBER / LEAD / LAG 等を利用）。
  - 外部 API 呼び出し（OpenAI, J-Quants）に対して堅牢なエラーハンドリングとリトライ戦略を採用。
  - DB への書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 相当の保存を想定）。

Fixed
-----
- N/A（初回リリースのため既知のバグ修正履歴はありません）。

Security
--------
- 環境変数の自動ロードで OS 環境変数を上書きしないデフォルト動作を採用し、意図しない機密情報上書きを防止。
- OpenAI API キー等が未設定の場合は ValueError を発生させ明示的に対処させる。

Notes / Implementation details
------------------------------
- OpenAI モデル: gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で使用。
- ニュースの時間ウィンドウ（JST/UTC の変換）は calc_news_window で一元管理。
- ai/news_nlp と ai/regime_detector は OpenAI 呼び出しの内部ヘルパー関数名を分離しており、モジュール間でプライベート関数を共有しない設計になっている（テスト時の patch 容易性を考慮）。
- DuckDB バインドの互換性考慮（executemany に空リスト不可等）に対応するロジックを実装。
- ロギングを各モジュールで使用し、処理結果や警告・例外情報を記録するようにしている。

Contributors
------------
- 初期実装チーム（ソースコードからの推測に基づくため省略可能）

今後の予定（想定）
-------------------
- 単体テストの整備（特に OpenAI 呼び出しのモック・DuckDB テストデータ）。
- J-Quants / kabuAPI クライアントの具体的実装と統合。
- モニタリング・実行コンポーネント（execution, monitoring）と戦略（strategy）モジュールの具体的実装。