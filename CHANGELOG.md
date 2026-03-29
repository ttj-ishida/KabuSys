CHANGELOG
=========

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初回公開バージョンを含む変更点の要約は以下の通りです。

1.0 未満のリリースは安定 API を保証しない可能性があります。  
（注: バージョンはパッケージ内の __version__ を参照しています）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py を追加し、
    data, strategy, execution, monitoring を公開対象とする __all__ とバージョンを定義。

- 設定・環境変数管理モジュール (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント行・export プレフィックス・クォート内エスケープ・インラインコメント取り扱いに対応）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装。
  - 環境変数保護（既存 OS 環境変数は .env.local の override から除外）を実装。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須キー取得メソッドを備える。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証を実装。

- AI（NLP）モジュール (src/kabusys/ai/*.py)
  - ニュースセンチメントスコアリング: score_news を実装（gpt-4o-mini + JSON mode を使用）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、バッチで OpenAI に送信。
    - バッチサイズ、記事数・文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx）、レスポンス検証、スコアの ±1.0 クリップを実装。
    - レスポンス JSON の前後余計テキストが混ざる場合の復元処理を実装。
    - API 呼び出し用の内部関数はテスト時に差し替え可能（unittest.mock.patch を想定）。
    - スコアは ai_scores テーブルへ idempotent（DELETE→INSERT）で書き込み、部分失敗時に他銘柄データを保護。

  - 市場レジーム判定: score_regime を実装
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily/raw_news を参照。LLM 呼び出し失敗時は macro_sentiment = 0.0 のフォールバック。
    - LLM は gpt-4o-mini を使用。再試行 / バックオフ・JSON パース検証等を実装。
    - 計算結果は market_regime テーブルへトランザクションで冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。エラー時は ROLLBACK を試行。

  - 共通設計方針:
    - datetime.today()/date.today() を直接参照せず、外部から target_date を受け取ることでルックアヘッドバイアスを回避。
    - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で指定可能・検証あり。

- データ基盤モジュール (src/kabusys/data/*.py)
  - カレンダー管理 (calendar_management.py)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベースでフォールバック（土日を非営業日扱い）。
    - DB 登録値がある場合は DB 値を優先し、未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar に冪等的に保存（バックフィル・健全性チェックあり）。

  - ETL パイプラインユーティリティ (pipeline.py / etl.py)
    - ETLResult データクラスを実装（ETL 実行結果の集約・シリアライズ to_dict を提供）。
    - 差分取得・バックフィル・保存の方針を文書化（jquants_client と quality モジュールを利用する設計）。
    - data/etl.py で ETLResult を再エクスポート。

- リサーチ（ファクター）モジュール (src/kabusys/research/*.py)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を使用）。
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS=0/欠損時は None）。
    - いずれも DuckDB 内 SQL を活用した実装で、データ不足時は None を返す振る舞いを明確化。

  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損・同順位処理を考慮）。
    - rank, factor_summary: ランク変換（同順位平均）・統計サマリーを実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB で処理する方針。

Other changes / notes
- DuckDB を主要なデータストアとして想定しており、多くの関数は DuckDB 接続オブジェクトを引数として受け取る設計。
- DB 書き込みは可能な限り冪等（DELETE→INSERT, ON CONFLICT 相当）かつトランザクション（BEGIN/COMMIT/ROLLBACK）で行う実装になっている。
- OpenAI への呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用。API レスポンスの不整合に対する復元ロジックを用意している。
- フェイルセーフ設計: API 失敗時やデータ不足時は例外を投げる代わりに中立値（例: ma200_ratio=1.0, macro_sentiment=0.0）を使って処理を継続する箇所がある。
- テスト容易性: OpenAI 呼び出し箇所（_call_openai_api）は patch 可能にしてユニットテストで外部依存を切り離しやすくしている。
- 設定関連の必須環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）が未設定の場合は Settings のプロパティが ValueError を投げる仕様。

Security
- API キー等の機密情報は Settings API で明示的に取得する設計。config モジュールは OS 環境変数を優先し、.env ファイルの読み込みは保護（既存 OS 環境変数は上書きされない）されている。

Known issues / limitations
- DuckDB のバージョン依存で executemany に空リストを渡せない制約に対応したコードがある（空リストを回避してから executemany を呼ぶ）。
- OpenAI のレスポンスが仕様外だった場合はスコア取得をスキップする実装で、部分的にスコアが欠落する可能性がある。呼び出し側でリトライや監視を行うことを推奨。
- 一部のユーティリティは jquants_client / quality 等の別モジュールに依存しており、実行にはそれらの実装・設定が必要。

---

アンカーテキストやリリースノートのリンクは現時点では未設定です。ドキュメントや API の安定化に伴い、次バージョンで Breaking changes / Fixed / Deprecated などのセクションを追加していきます。