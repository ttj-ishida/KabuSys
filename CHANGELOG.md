CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

なし

0.1.0 - 2026-04-02
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ概要:
    - src/kabusys/__init__.py によりバージョン番号と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - 環境設定/読み込み:
    - src/kabusys/config.py
      - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
      - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、CWD に依存しない方式を採用。
      - .env / .env.local の読み込み順を定義（OS 環境変数 > .env.local > .env）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
      - クォートやエスケープ、inline コメント等に対応した .env 行パーサを実装（export 形式にも対応）。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル等の設定をプロパティで取得可能。未設定の必須値は ValueError を発生させる。
      - 環境変数検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

  - AI モジュール:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を使用し、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
      - JSON Mode（厳密な JSON）を期待しつつ、パースの耐性（前後余計なテキストから最外の {} を抽出）を実装。
      - バッチサイズ、記事数、文字数上限、リトライ（429/ネットワーク/5xx）と指数バックオフを備えた堅牢な API 呼び出しロジックを実装。
      - レスポンス検証（results キー・型チェック・コード整合性・数値チェック）および ±1.0 でのクリッピングを行う。
      - DuckDB へは部分置換（DELETE → INSERT）で冪等に書き込み。空パラメータによる executemany の問題（DuckDB 0.10）に配慮。
      - API キーは引数で注入可能、なければ OPENAI_API_KEY 環境変数を使用。未設定時は ValueError。

    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース（マクロキーワード）の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - prices_daily / raw_news を参照してma200_ratio を計算、マクロNewsは最大 20 記事まで抽出し OpenAI（gpt-4o-mini）へ送信。
      - API の失敗やレスポンス不正時はフェイルセーフとして macro_sentiment = 0.0 を採用し処理を継続。
      - 結果は market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に書き込み。DB 書き込み失敗時は ROLLBACK を試み、上位へ例外を伝播。
      - API 呼び出し関数はテストで差し替え可能（モックしやすい設計）。OpenAI API のエラー分類に基づくリトライ戦略を実装。

  - Research（ファクター・特徴量探索）:
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）などのファクター計算関数を提供。
      - DuckDB のウィンドウ関数を活用した効率的な SQL 実装。データ不足時は None を返すなど堅牢化。
    - src/kabusys/research/feature_exploration.py
      - 将来リターンの計算（任意ホライズン）・IC（Spearman のランク相関）計算・統計サマリー（count/mean/std/min/max/median）・ランク化ユーティリティを実装。
      - 外部ライブラリに依存せず純粋 Python（標準ライブラリ）で実装。
    - src/kabusys/research/__init__.py
      - 主要関数と zscore_normalize（data.stats から）を再エクスポート。

  - Data（ETL / カレンダー）:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー（market_calendar）を管理するユーティリティ群を追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar が未取得のときは曜日ベース（土日除外）でフォールバックする設計。DB に部分的にしかデータがない場合でも一貫した判定を返す。
      - カレンダー夜間バッチ（calendar_update_job）を実装。J-Quants クライアントを通した差分取得と冪等保存、バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py
      - ETL パイプライン用 ETLResult dataclass と差分更新・保存・品質チェックのためのユーティリティを実装。jquants_client と quality モジュールに依存。
      - ETLResult により品質問題やエラー情報を収集・出力できるように設計。
    - src/kabusys/data/etl.py
      - ETLResult の再エクスポート。

  - その他:
    - DuckDB を主なローカル DB として使用する設計に統一（関数シグネチャに DuckDB 接続を明示）。
    - OpenAI クライアント注入・例外処理・ログ出力に配慮した堅牢な実装方針を採用。
    - 日付取り扱いは全て date/naive datetime を使用し、datetime.today()/date.today() の参照を最小限にしてルックアヘッドバイアスを回避する方針を明示的に採用。

Changed
- 初版リリースのため該当なし（新規追加）。

Fixed
- 初版リリースのため該当なし（新規追加）。

Security
- API キーは可能な限り引数で注入することを推奨（テスト容易性と鍵管理の観点から）。
- 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト/安全な実行のため）。

Known limitations / Notes
- OpenAI モデルは gpt-4o-mini を前提。将来的なモデル変更時にプロンプト/レスポンスパースの調整が必要になる可能性がある。
- DuckDB の executemany に関するバージョン差異（空リスト不可等）に対処するコードが含まれるため、DuckDB のバージョン依存性に留意してください。
- jquants_client、quality モジュール等は外部依存（別モジュール）として参照しており、実行にはそれらの実装が必要です。
- monitoring はパッケージ公開対象として __all__ に含まれるが、今回のリリースには具体的ファイルが含まれていない点に注意してください（将来追加予定）。

如何なる追加情報が必要か、あるいは過去のコミット履歴に基づいたより詳細な差分表現を望む場合は、対象の Git コミットログや変更前後のファイル差分を提供してください。