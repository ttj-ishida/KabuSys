Changelog
=========
すべての変更は Keep a Changelog の慣習に従い記載しています。  
慣例: 変更は "Added", "Changed", "Fixed", "Security" 等のカテゴリで分類しています。

Unreleased
----------
- (なし)

[0.1.0] - 2026-03-29
--------------------
Added
- パッケージ初期実装を追加。
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を含む）。
- 設定管理（kabusys.config）を追加。
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントの取り扱いに対応した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants, kabu, Slack, DB パス等）。
  - 環境値検証: KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証ロジックを実装。
  - デフォルトの DB パス: duckdb は data/kabusys.duckdb、sqlite は data/monitoring.db。
- AI 関連モジュール（kabusys.ai）を追加。
  - news_nlp: ニュース記事をまとめて OpenAI API（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算、記事集約（銘柄毎、記事数や文字数のトリム）、バッチ処理（最大20銘柄/リクエスト）。
    - JSON Mode 応答の検証と堅牢なパース処理。部分失敗時に既存スコアを保護するため書き込みは対象コードのみ置換（DELETE → INSERT）。
    - ネットワークエラー・429・タイムアウト・5xx に対する指数バックオフと再試行を実装。
    - テスト容易性のため OpenAI 呼び出し関数をパッチ可能に実装（unittest.mock.patch を想定）。
    - ルックアヘッドバイアス回避の設計（datetime.today() を使わず target_date 指定）。
  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュースのLLMセンチメントを合成して market_regime テーブルへ日次判定を行う機能。
    - ma200_ratio（200日MA乖離）計算、マクロニュース抽出（キーワードベース）、OpenAI でのマクロセンチメント評価、重み付け合成（70%/30%）、閾値によるラベル付与（bull/neutral/bear）。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
- Research モジュール（kabusys.research）を追加。
  - factor_research: モメンタム（1/3/6ヶ月）、200日MA乖離、ATR20、出来高・売買代金等のファクター計算を実装。
    - DuckDB を使ったウィンドウ関数ベースの計算。データ不足時に None を返す設計。
  - feature_exploration: 将来リターン calc_forward_returns、IC（Spearman）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - horizons 検証、ランクの同順位処理（平均ランク）や ties 対策（round 誤差対処）。
    - pandas 等に依存せず標準ライブラリで実装。
- Data モジュール（kabusys.data）を追加。
  - calendar_management: JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間カレンダー更新ジョブ（calendar_update_job）を実装。
    - market_calendar の有無に応じた曜日フォールバックロジック、最大探索日数制限、バックフィル期間、健全性チェックを実装。
  - pipeline / etl: ETL パイプラインの基礎を実装（差分取得、保存、品質チェックフック）。
    - ETLResult dataclass を提供し、品質問題とエラーの集約・辞書変換を可能に。
    - DuckDB の互換性（executemany に空リスト不可）を考慮した実装。
  - jquants_client（外部クライアント実装を参照する想定）との連携ポイントを用意（fetch/save 関数を呼び出す）。
- テストフレンドリー設計を多数反映。
  - OpenAI 呼び出しの差し替えポイント、環境自動ロードをオフにするフラグなど。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- OpenAI API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げることで意図せぬ API 呼出を防止。
- .env 読み込みで OS 環境変数を保護する protected 機構を導入（既存環境変数を意図せず上書きしない）。

Notes / 実装上の重要点・互換性
- ルックアヘッドバイアス対策: すべての分析関数は内部で date/datetime.today() を参照せず、呼び出し側が target_date を明示的に渡すことを前提に実装しています。
- DuckDB 互換性: executemany に空リストを渡すと失敗するバージョンを考慮して、空リストチェックを行っています。
- OpenAI 呼び出し: gpt-4o-mini を想定し JSON Mode を利用する形で実装。レスポンスの JSON パース失敗や予期しない出力は堅牢に扱い、失敗時は該当処理をスキップまたはメトリクスに 0.0 を使うフォールバックを行います。
- DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK ハンドリング）。
- カレンダー未登録日は曜日ベースでフォールバックするため、market_calendar の部分取得状態でも一貫した営業日判定が可能。
- 環境変数の自動ロードはプロジェクトルート探索で .git や pyproject.toml を参照するため、パッケージ配布後の CWD に依存しない設計。

Upgrade / Migration Notes
- 初回公開バージョンのため、既存ユーザー向けの移行手順はなし。将来的に設定名や DB スキーマを変更する場合は明示的なマイグレーションを提供予定。

貢献者
- kabusys 開発チーム（初期実装）

補足
- ソース内に API 呼び出しやデータ保存の参照先（jquants_client 等）が存在しますが、外部サービスの具体的実装・認証情報はユーザー環境で設定する必要があります（.env 参照）。
- 何か特定機能の詳細（例: ai スコアの閾値やバッチサイズなど）を CHANGELOG に追加したい場合は指示してください。