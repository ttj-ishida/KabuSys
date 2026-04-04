CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。
リリース日はコードベースから推測した日付を使用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - 高水準のモジュール構成:
    - kabusys.config: 環境変数 / .env 管理（自動読み込み機能を備え、.env, .env.local の優先度制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート）
      - .env パーサは export KEY=val 形式、シングル／ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。
      - 環境変数保護（既存の OS 環境変数を上書きしない、override/ protected の概念）。
      - Settings クラス: J-Quants / kabu API / LINE / DB パス / 監視設定 / ログレベル等のプロパティを提供。入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
    - kabusys.ai:
      - news_nlp モジュール:
        - raw_news / news_symbols をもとに銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄単位のセンチメント（ai_score）を生成し ai_scores テーブルへ書き込む処理を実装。
        - 時間ウィンドウ計算（JST基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。
        - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数/文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）とフォールバック設計。
        - レスポンスの厳密なバリデーション、JSON パースの回復処理（余分な前後テキストから最外側の {} を抽出）、スコアの ±1.0 クリップを実装。
        - テスト容易性のため _call_openai_api を patch 可能に設計。
      - regime_detector モジュール:
        - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う処理を実装。
        - prices_daily からのデータ取得は target_date 未満（排他）に制限し、ルックアヘッドバイアスを排除。
        - OpenAI 呼び出しでのリトライ・5xx 判定・フォールバック（失敗時は macro_sentiment=0.0）を実装。
        - API キーは引数で注入可能、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
    - kabusys.data:
      - calendar_management モジュール:
        - JPX カレンダー（market_calendar）管理と営業日判定ロジックを提供。DB 登録がある場合は DB 値を優先、登録がない日については曜日ベースでフォールバックする一貫した振る舞いを実装。
        - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day といったユーティリティ関数を実装。
        - calendar_update_job: J-Quants API（jquants_client を利用）から差分取得し冪等保存するジョブ。バックフィル、健全性チェック、ログ出力を実装。
      - pipeline / etl:
        - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題・エラーの収集を含む）。
        - ETL モジュール設計に基づく差分取得、backfill、品質チェックの方針を反映（実装の骨子を提供）。
      - その他: jquants_client 連携を想定した関数呼び出し箇所を用意。
    - kabusys.research:
      - factor_research モジュール:
        - モメンタム（1m/3m/6m リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR / ATR%）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER / ROE）を DuckDB の prices_daily/raw_financials を用いて計算する関数を実装。
        - データ不足時の None 処理、SQL ベースでの効率的なウィンドウ計算を実装。
      - feature_exploration モジュール:
        - 将来リターン計算（任意 horizon のリード）calc_forward_returns。
        - Spearman のランク相関（IC）を計算する calc_ic、ランク化ユーティリティ rank、ファクター統計サマリー factor_summary を提供。
    - パッケージ初期化:
      - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Security / Robustness / Design
- ルックアヘッドバイアス対策: news_nlp/regime_detector/research モジュール全てで datetime.today()/date.today() を直接参照せず、target_date 引数を用いる設計。
- DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）を使用し、例外発生時は ROLLBACK を試行、失敗した場合は警告ログを出力。
- OpenAI 呼び出しは明示的なリトライ戦略（指数バックオフ）を実装、5xx とそれ以外のエラーを区別して扱う。
- テストを想定した設計（_call_openai_api の patch 可能、API キー注入など）を導入。
- 型ヒント、詳細な docstring、ログ出力（INFO/DEBUG/WARNING/EXCEPTION）を多数追加。

Documentation / Notes
- モジュールごとに処理フロー・設計方針が docstring に明記されており、実装意図とフェイルセーフの振る舞いが記載されている。
- news_nlp の出力仕様では LLM に厳密な JSON 出力を要求しているが、パース回復ロジックも組み込まれている。
- calc_value では PBR や配当利回りは未実装である旨が明記されている（今後の拡張ポイント）。

Known issues / Limitations
- jquants_client（外部 API クライアント）の実装は本差分に含まれていないため、実行環境では別途実装/提供が必要。
- OpenAI の実際のレスポンス形式や API バージョンの変化に伴う互換性問題は将来的に発生する可能性がある（現状は SDK の例外や status_code 変化へある程度対応）。
- DuckDB の一部バージョン差異（executemany の空リスト制約など）を回避するための実装上の配慮があるが、環境依存の動作差は完全には排除できない。

Authors
- コードベースから推測した設計・実装に基づいて作成。

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はコミットログ・PR 等の情報を参照して適宜補正してください。）