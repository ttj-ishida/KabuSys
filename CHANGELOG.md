# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
日付はリリース日を示します。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買／データ基盤向けのコアライブラリを追加しました。主な機能、設計方針、堅牢性対応を以下に記載します。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加 (kabusys.__version__ = 0.1.0)。
  - モジュール公開一覧: data, strategy, execution, monitoring。

- 環境設定 (kabusys.config)
  - .env ファイルと環境変数からの設定読み込み機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー: コメント、export プレフィックス、シングル／ダブルクォート、エスケープシーケンス、インラインコメント等に対応。
  - 既存 OS 環境変数を保護する protected 機構（.env 上書き制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティ経由で取得（必須項目は未設定で ValueError を発生）。

- AI ニュース・レジーム判定 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - 指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく raw_news の集約、銘柄ごとのテキスト結合・トリム。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（1回最大20銘柄）。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）をエクスポネンシャルバックオフで実装。
    - レスポンスの厳密検証（JSON 抽出、results リスト、code/score の型検査、未知コード除外、数値の有限性確認）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。部分失敗時に既存スコアを保護するロジックあり。
    - テスト容易性のため OpenAI 呼び出し部分をモック可能（_call_openai_api の差し替え）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（225連動）の200日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し日次でレジームを判定（bull/neutral/bear）。
    - ニュースセンチメントは OpenAI を用いて JSON 出力（{"macro_sentiment": n}）から取得。記事がない場合は LLM 呼び出しは行わず 0.0 を採用。
    - API エラー時は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT, エラー時は ROLLBACK を試行）。
    - ルックアヘッドバイアス回避のため日付比較は排他条件（date < target_date 等）で実装。

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルベースの営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未登録日や NULL 値に対する曜日ベースのフォールバック（週末: 土日非営業日）。
    - 夜間バッチ更新ジョブ calendar_update_job により J-Quants から差分取得・バックフィル・冪等保存を実装。健全性チェックを導入（極端に未来日がある場合はスキップ）。
  - ETL パイプライン (pipeline.ETLResult を公開)
    - 差分更新、保存（jquants_client の save_* を利用した冪等保存）、品質チェック呼び出しを想定した ETLResult データクラスを追加。
    - ETL 実行結果の要約（取得数・保存数・品質問題・エラー）を保持し、辞書変換用 to_dict を提供。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、ターゲット日の調整等。

- リサーチ（kabusys.research）
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6Mリターン、ma200乖離）、ボラティリティ・流動性（20日ATR、相対ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上で SQL と Python 組合せで計算する関数を追加。
    - データ不足時の None 処理、結果は (date, code) ベースの dict リストで返却。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman ランク相関）、統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - rank は同順位を平均ランクで扱い、丸め処理で浮動小数の ties 検出漏れを防止。

### 変更 (Changed)
- （初回リリースのため既存コードからの変更はありません）

### 修正 (Fixed)
- （初回リリースのため修正履歴はありません）

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- 環境変数の自動読み込みで OS 環境変数を保護する設計を導入（.env による上書きを防ぐ protected set）。
- OpenAI API キーや各種トークンは Settings で必須項目として扱い、未設定時は明示的に例外を発生させる（利用者に誤った運用を気付きやすくする）。

### 実装上の注意・設計方針（重要）
- ルックアヘッドバイアス回避: datetime.today() / date.today() を内部ロジックで使わず、必ず caller が target_date を与える設計。
- フェイルセーフ: 外部 API の失敗時は例外を投げず安全側の既定値（例: 中立スコア 0.0 や ma200_ratio=1.0）で継続する箇所がある（ログ出力は行う）。
- 冪等性: DB 書き込みは冪等となるよう DELETE → INSERT や ON CONFLICT 相当の保存を想定。
- テスト容易性: OpenAI 呼び出し部はモックしやすいよう抽象化されている（ユニットテストで差し替え可能）。
- DuckDB のバージョン差分や制約（executemany に空リスト不可等）に配慮した実装。

---

今後の予定（参考）
- strategy / execution / monitoring モジュールの具体的な取引ロジック・発注実装の追加。
- より細かな品質チェック、テストカバレッジ拡充、運用向け監視・アラート機能。
- OpenAI 呼び出しのコスト最適化やモデル切替の抽象化。

（注）本 CHANGELOG はソースコードの docstring・実装・設計コメントから推測して作成しています。実際のプロダクトリリースノートとして使用する場合は、差し戻し・追補を行ってください。