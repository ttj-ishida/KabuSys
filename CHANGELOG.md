CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記述しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

Unreleased
----------
（なし）

0.1.0 - 初回リリース
-------------------

Added
- パッケージ初版を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本モジュール:
  - kabusys.config
    - .env ファイルおよび環境変数から設定を自動読み込みする実装を追加。
    - 自動読み込みの探索は __file__ を起点に .git または pyproject.toml を辿ることでプロジェクトルートを特定（CWD に依存しない）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env のパースは以下に対応:
      - 空行 / コメント行（#）のスキップ
      - export KEY=VAL 形式のサポート
      - シングル・ダブルクォート内でのバックスラッシュエスケープ処理
      - インラインコメントの扱い（クォート無い場合は直前が空白の `#` をコメントとみなす）
    - 環境変数必須チェック用の _require と Settings クラスを提供。J-Quants, kabu API, Slack, DB パス等のプロパティを持つ。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）、LOG_LEVEL の検証を実装。
    - デフォルトの DB パス（DuckDB / SQLite）を設定（data/kabusys.duckdb, data/monitoring.db）。

- データプラットフォーム関連:
  - kabusys.data.calendar_management
    - market_calendar テーブルを利用した営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダー情報がない場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェック付き）。
    - 最大探索日数やバックフィル期間などの安全パラメータを導入。

  - kabusys.data.pipeline / kabusys.data.etl
    - ETLResult データクラスを追加し、ETL 実行結果の集約（取得数・保存数・品質問題・エラー）を保持。
    - 差分取得・バックフィル・品質チェックの設計方針に沿った基盤を提供。
    - DuckDB に対する最大日付取得やテーブル存在チェック等のユーティリティを実装。
    - DuckDB 0.10 の executemany の制約（空リスト不可）を考慮した実装。

  - jquants_client を想定した ETL ワークフローの支援（jquants_client の具体実装は外部）。

- リサーチ / ファクター関連:
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum
      - calc_volatility
      - calc_value
    - DuckDB の SQL ウィンドウ関数を多用し、データ不足時は None を返す設計。
    - 長期スキャン範囲や ATR 計算での NULL 伝播制御などの実務的配慮を実装。

  - kabusys.research.feature_exploration
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証付き）
    - IC（Spearman ランク相関）計算: calc_ic（欠損や ties を適切に扱う）
    - ランク付けユーティリティ: rank（同順位は平均ランク、丸めで ties 検出の安定化）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）

  - これらは外部データフレームライブラリに依存せず、標準ライブラリ + DuckDB のみで実装。

- AI（LLM）統合:
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを取得する処理を実装。
    - 機能のハイライト:
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
      - 1 銘柄あたりの記事数・文字数上限（記事数: 10 件、文字数: 3000）によるトリム
      - 最大バッチサイズ 20 銘柄でのチャンク処理
      - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ
      - レスポンスの堅牢なバリデーション（JSON 抽出・results キー・コード照合・数値チェック）
      - スコアの ±1.0 クリップ、部分成功時は既存スコアを保護するため対象コードのみ置換（DELETE → INSERT）
      - テスト容易性のため _call_openai_api をパッチ差し替え可能
      - API キー解決（引数優先、環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError を送出。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - 特徴:
      - ma200_ratio の計算は target_date 未満のみを参照しルックアヘッドを排除
      - マクロニュースはニュースフィルタ（キーワード群）で抽出し、LLM による JSON レスポンスをパース
      - LLM 呼び出しのリトライ・フォールバック（全リトライ失敗時 macro_sentiment=0.0）
      - レジームスコアはクリップして閾値でラベル付け
      - 結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

- 共通の信頼性改善 / 実装上の配慮:
  - DuckDB を想定した SQL 実装で互換性に配慮（空の executemany 対応、日付の型変換処理）。
  - 重要な DB 書込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時は警告ログを出力するようにした。
  - LLM 呼び出し系は APIError の status_code に応じてリトライ判定を行い、5xx 系は再試行の対象とする。
  - ルックアヘッドバイアスを避けるため、score_news / score_regime 等は内部で datetime.today() / date.today() を参照しない設計。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Deprecated
- （初版につき該当なし）

Removed
- （初版につき該当なし）

Security
- 環境変数が未設定の場合は明示的に ValueError を送出して早期検出する設計（OpenAI API キー / Slack トークン 等）。

補足
- OpenAI モデルは暫定で gpt-4o-mini を使用する実装となっている（将来的なモデル切替に対応しやすい設計）。
- 実際の外部 API（J-Quants, kabuステーション, OpenAI）のクライアント実装や認証は、それぞれのモジュール（例: jquants_client）に依存する想定。今回収録したコードは主にデータ処理・ETL・解析・AI 呼び出しのワークフローを提供する層です。