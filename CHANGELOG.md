Keep a Changelog — kabusys

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

v0.1.0 — 2026-04-09
-------------------
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点と設計上の特徴は以下のとおりです。

Added
- パッケージ基盤
  - パッケージ名 kabusys を導入。__version__ = "0.1.0" を設定し、公開サブパッケージとして data, research, ai, execution, monitoring, strategy (一部は __all__ に記載) を想定。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動的に読み込む仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から探索するため、CWD に依存しない。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装: export 形式、引用符付き値、エスケープシーケンス、行内コメント等を取り扱い。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連のプロパティを環境変数から取得（必須項目はエラーを投げる）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- データ層 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と夜間バッチ更新 job（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。最大探索範囲を設定して無限ループを防止。
    - J-Quants クライアント経由で差分取得 → 冪等保存（save_market_calendar）を行う設計。
  - ETL パイプライン:
    - pipeline モジュールを実装し、ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（idempotent）、品質チェックの流れを想定した設計。
    - backfill やカレンダー先読み、品質問題の集約（致命的問題があっても処理を継続する方針）を採用。
    - DuckDB 互換性（executemany の空リスト制約等）に配慮した実装。
- AI / NLP (kabusys.ai)
  - news_nlp:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを算出して ai_scores テーブルへ書き込むワークフローを実装。
    - ニュース収集ウィンドウ（JST 前日15:00〜当日08:30）を calc_news_window で計算（UTC naive datetime で返却）。
    - バッチ処理（最大 20 銘柄/回）、入力トリミング（記事数上限・文字数上限）、JSON Mode を想定したレスポンス検証、スコアクリップ（±1.0）を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライと、非リトライエラーでのフェイルセーフ（失敗したチャンクはスキップ）。
    - テスト容易化のため _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - MA 計算、マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行戦略、フェイルセーフ（API 失敗時 macro_sentiment=0）を備える。
    - ルックアヘッドバイアス防止（target_date 未満データのみ使用、datetime.today() を参照しない）を設計要件として実装。
- リサーチ（kabusys.research）
  - factor_research:
    - Momentum/Value/Volatility などの定量ファクター計算を実装。
      - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日データ不足時は None）。
      - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
      - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新財務データを取得）。
    - DuckDB のウィンドウ関数等を利用して効率的に計算。外部 API へのアクセスは行わない。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）に基づく IC 計算（同順位は平均ランクで処理）。
- ロギング・診断
  - 各モジュールで操作ログ・警告・例外ログを適切に出力する実装（logger を使用）。
  - DB 書き込みはトランザクション制御（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK）で冪等性と整合性を確保。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

設計上の注意（ドキュメント的補足）
- ルックアヘッドバイアス防止:
  - AI スコアリング / レジーム判定 / ファクター計算で datetime.today()/date.today() を直接参照しない設計。すべて target_date を明示して計算することで実運用・バックテストでのバイアスを回避。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出し失敗時は例外で停止させず、局所的にフォールバックして処理を継続する箇所が多い（API 失敗時はスコアを 0.0 にする、失敗チャンクはスキップ 等）。
- テスト性:
  - OpenAI 呼び出し部分はモジュール内の private 関数（_kall_openai_api 等）を patch して差し替えられるよう設計しており、単体テストが行いやすい。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョンに配慮したガード処理が存在する（空パラメータ時は呼ばない）。

今後の予定（想定）
- execution / monitoring / strategy 各モジュールの実装拡充（__all__ に記載あり）。
- 追加の品質チェック・監視アラート、稼働環境向けの設定/デプロイ手順追記。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）との整合性チェックとリファイン。

もし特定ファイルや変更点ごとにより詳細な説明（例: 関数一覧、引数・戻り値のサンプル、設計意図の深掘り）が必要であれば、どのモジュールについて詳述するかを教えてください。