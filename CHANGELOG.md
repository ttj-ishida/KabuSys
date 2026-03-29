# Changelog

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
このファイルは、コードベース（kabusys）から推測できる機能追加・設計方針・フェイルセーフ等をまとめた初期リリースの変更履歴です。

全般的な方針:
- DuckDB を用いたローカルデータプラットフォームを前提に設計（外部発注 API へはアクセスしないモジュールを分離）。
- ルックアヘッドバイアス対策として datetime.today()/date.today() の直接参照を避け、関数引数で基準日を受け取る設計。
- OpenAI（gpt-4o-mini）を用いた NLP 処理はフェイルセーフ（API失敗時はスコアを 0.0 にフォールバック、例外非伝播の設計）とし、テスト容易性のため API 呼び出し点をモック可能に実装。
- DB 書き込みは冪等性を考慮（DELETE → INSERT の置換や ON CONFLICT 相当の保存を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初期公開
  - kabusys パッケージの __version__=0.1.0 と主要サブパッケージのエクスポート設定を追加（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env / .env.local ファイルの自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサを実装（export 形式対応、シングル/ダブルクォートとエスケープ対応、インラインコメント処理）。
  - 環境変数必須チェック用 _require と Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス等のプロパティ）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーションを実装。
  - デフォルト DB パス（duckdb / sqlite）と is_live / is_paper / is_dev のユーティリティプロパティを追加。

- ニュース NLP（OpenAI を用いたセンチメント） (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols から銘柄ごとにニュースを集約して OpenAI へバッチ送信し ai_scores テーブルへ書き込む機能を実装。
  - 時間ウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC で扱う calc_news_window）を提供。
  - バッチサイズ（最大 20 銘柄）、1銘柄あたり最大記事数（10件）・最大文字数（3000 文字）でトリム。
  - OpenAI 呼び出しは JSON Mode を利用し、429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
  - レスポンスの厳密なバリデーションを実装（results 配列、code と score、スコア数値・有限値チェック、未知コードの無視）。
  - スコア値は ±1.0 にクリップ。部分失敗時に既存データを保護するため、対象コードのみ DELETE → INSERT で更新（DuckDB 互換性考慮）。
  - テスト性を考慮し _call_openai_api をモック差し替え可能に設計。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
  - MA200 比率の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）にフォールバック。
  - マクロニュース抽出はキーワードベースで抽出（最大 20 件）、LLM モデル gpt-4o-mini を使用して JSON 応答を期待。
  - API 呼び出し失敗・パース失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
  - 合成スコアを -1.0〜1.0 にクリップし閾値でラベル付け。結果を market_regime テーブルへ冪等的に書き込み（DELETE/INSERT をトランザクション内で実行）。
  - OpenAI クライアント生成ポイントとキー注入（api_key 引数）でテスト/操作性を向上。

- データプラットフォーム: カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar テーブルに基づく営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB データが存在しない場合は曜日ベースのフォールバック（土日は非営業日扱い）。
  - next/prev_trading_day は探索上限（最大 60 日）を設けて無限ループを防止。
  - カレンダー夜間バッチ更新 job (calendar_update_job) を追加。J-Quants API から差分取得 → 保存（バックフィル 7 日） → 保存件数を返す。最終取得日の異常チェックあり。

- ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を定義し、ETL の取得件数・保存件数・品質チェック結果・エラーを集約可能に。
  - 差分更新、backfill（デフォルト 3 日）方針、品質チェック統合の設計を反映。
  - jquants_client を通じた idempotent 保存と品質チェック呼び出しの想定がドキュメント化。
  - etl モジュールで ETLResult を再エクスポート。

- 研究系ユーティリティ (src/kabusys/research/)
  - factor_research: モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) 計算関数を追加。すべて DuckDB の SQL を主体に実装し (date, code) キーで結果を返す。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR / ATR 比率 / 20 日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials から報告日の直近財務データを取得し PER / ROE を計算。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（スピアマン）計算(calc_ic)、ランク変換(rank)、統計サマリー(factor_summary) を追加。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応し入力検証あり。
    - calc_ic はランク相関（スピアマン）を実装し、データ不足（<3）で None を返す。
    - factor_summary は count/mean/std/min/max/median を計算。

- テスト/デバッグに役立つログ・警告の整備
  - データ不足や API パースエラー、ROLLBACK 失敗等に対する警告ログを多数追加。

### 変更 (Changed)
- 初期実装のため該当なし（新規追加がメイン）。

### 修正 (Fixed)
- 初期実装のため該当なし。

### 既知の注意点 / 設計上の制約
- OpenAI 呼び出しは外部ネットワークに依存するため、テスト時は _call_openai_api をモックすることを想定。
- DuckDB の executemany に空リストを渡せないバージョン互換性を考慮して、空チェックを入れている箇所がある。
- news_nlp / regime_detector 共に JSON Mode を前提とするため、LLM 応答の形式変化に対して厳密なバリデーションで耐性を持たせているが、応答設計変更には注意が必要。
- calendar_update_job 等は外部 J-Quants クライアント（jquants_client）に依存しており、API 側のスキーマ変更は影響を受ける可能性あり。

---

（本 CHANGELOG.md は、与えられたコードベースの実装内容とドキュメンテーション文字列から推測して作成しています。実際のリリースノートや公開日・変更履歴は実プロジェクトの管理方針に従って調整してください。）