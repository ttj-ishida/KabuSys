CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。

フォーマット:
- Unreleased: 今後の変更（未リリース）
- 各リリースはバージョンとリリース日を持ち、Added / Changed / Fixed / Security 等のセクションで構成します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-04
--------------------

Initial release — 日本株自動売買システムの初版リリース。

Added
- パッケージ基盤
  - kabusys パッケージ初期化。__version__ = "0.1.0" を設定し、主要サブパッケージを公開 (data, strategy, execution, monitoring)。
- 設定管理 (kabusys.config)
  - .env ファイルと OS 環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト向け）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーシングの堅牢化:
    - export KEY=val 形式、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
    - override/protected 機能で既存 OS 環境変数を保護しつつ .env.local による上書きを可能に。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム関連設定のプロパティを用意。
    - 必須環境変数未設定時に明確な ValueError を送出。
    - env/log_level に対する入力検証（許容値チェック）、is_live/is_paper/is_dev のユーティリティプロパティ。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を計算。
    - JST ベースのニュースウィンドウを明示（前日 15:00 JST ～ 当日 08:30 JST、DB 比較用に UTC naive datetime を返す）。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、JSON Mode のレスポンスバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルに差分（DELETE→INSERT）で書き込み、部分失敗時に既存データを保護。
    - テストフック: OpenAI 呼び出しを差し替え可能（_call_openai_api を patch できる）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジームを判定（bull/neutral/bear）。
    - LLM（gpt-4o-mini）を JSON 応答モードで呼び出し、API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - レジーム合成ロジック、閾値設定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しのリトライロジックとエラー種別別の扱いを明確化。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データがない場合は曜日ベースのフォールバック（週末除外）を提供し、DB とフォールバックの振る舞いを一貫させる設計。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の実行結果、品質チェック結果、エラーリスト等を格納）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client を介した idempotent 保存、品質問題の収集）。
  - etl パブリックインターフェース: ETLResult を再エクスポート。
- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1m/3m/6m リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None 設定、営業日ベースのスキャン範囲、SQL + Python の組合せで効率的に処理。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証）、IC（Spearman ランク相関 calc_ic）、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）の実装。
    - pandas 等外部ライブラリ依存なしで標準ライブラリと DuckDB のみで実装。
  - パブリック API のエクスポートを整備。
- ロギング・堅牢性
  - 多くの処理で詳細な logger 呼び出しを追加（情報・警告・例外ログ）。
  - DB 書き込みでのトランザクション管理（BEGIN/COMMIT/ROLLBACK）と rollback 失敗時の追加警告。
  - 外部 API 呼び出し失敗時に処理を継続するフェイルセーフ設計（LLM/外部API はスコア無しでスキップし、例外を抑制してログに記録）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （初版のため該当なし）

Notes / 設計上の注記
- ルックアヘッドバイアス対策:
  - AI スコアリング／レジーム判定／ETL／リサーチ関数はいずれも内部で datetime.today() / date.today() を直接参照せず、target_date 引数に基づいて処理する設計。
- テスト容易性:
  - OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、ユニットテスト時に patch して置き換え可能。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への配慮が随所にある（空チェック後に executemany を行う等）。
- idempotency:
  - ETL / カレンダー / AI スコア保存処理は既存レコードの上書き（DELETE→INSERT / ON CONFLICT）で冪等性を確保。

Breaking Changes
- なし（初回リリース）

既知の制限
- 一部機能は外部 API（OpenAI / J-Quants / kabuステーション 等）に依存するため、API キー未設定時は ValueError を送出する箇所がある。
- monitoring サブパッケージは __all__ に含まれているが、今回のコードベースでは具体的な実装ファイルが含まれていない可能性あり（将来的な追加予定）。

---- 

（補足）
この CHANGELOG は現在のソースコードから推測して作成しています。実際のリリースノートではリリース日、貢献者、マイグレーション手順などを必要に応じて追記してください。