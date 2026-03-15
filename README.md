# KabuSys

KabuSys は日本株の自動売買（アルゴリズムトレード）を想定した軽量なパッケージのスケルトンです。  
現在はパッケージ構成と基本情報のみを含む初期バージョン（v0.1.0）で、データ取得、売買戦略、注文実行、監視の各コンポーネントをモジュール単位で拡張できる設計になっています。

バージョン: 0.1.0

---

## 機能一覧（想定）

現状は骨組みのみですが、以下の機能を実装することを想定しています。

- データ取得モジュール（data）
  - 株価データの取得／キャッシュ
  - CSV/データベース等からの読み込みインタフェース
- 売買戦略モジュール（strategy）
  - シグナル生成ロジック（例: テクニカル指標、シンプルなルールベース）
  - バックテスト用のインタフェース
- 注文実行モジュール（execution）
  - ブローカーAPIへの注文送信（接続・約定管理・エラーハンドリング）
  - 注文送信の抽象化レイヤ
- 監視モジュール（monitoring）
  - ログ／アラート出力
  - 実行状況の可視化／ヘルスチェック

※ 実装はこれから追加する想定です。各パッケージに対して独自の実装を追加してください。

---

## 要件

- Python 3.8 以上（プロジェクトの方針に合わせて適宜調整してください）
- （オプション）ブローカーAPIやデータソースに依存する外部ライブラリは、実装時に追加します

---

## セットアップ手順

1. リポジトリをクローン（既にローカルにある場合は省略）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 開発用インストール（プロジェクトルートに `setup.py` / `pyproject.toml` がある想定）
   ```
   pip install -e .
   ```

4. 依存パッケージがある場合は requirements.txt や pyproject.toml に従ってインストールしてください。
   ```
   pip install -r requirements.txt
   ```

---

## 使い方（基本）

パッケージは以下のモジュールを提供する構成になっています：
- kabusys.data
- kabusys.strategy
- kabusys.execution
- kabusys.monitoring

最小の利用例（インポートとバージョン表示）:
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

開発者向けのワークフロー（例）:
1. data モジュールにデータ取得・前処理ロジックを実装する
2. strategy モジュールにシグナル生成クラスを実装する
3. execution モジュールにブローカー接続と注文送信の実装を追加する
4. monitoring モジュールでログや通知を組み込む
5. 上記を組み合わせて自動売買フローを構築・テストする

拡張例（ファイルを追加して戦略クラスを実装するイメージ）:
- src/kabusys/strategy/my_strategy.py を作成し、Strategy クラスを実装
- アプリケーションから import kabusys.strategy.my_strategy をして利用

注意:
- 実際の注文実行を行う際は、ブローカーAPI の利用規約や日本の法規制、リスク管理を必ず確認してください。
- 本パッケージは自動売買のための土台です。実運用前に十分な検証と安全策（注文上限、損失制限、監視体制）を実装してください。

---

## ディレクトリ構成

現在の最小構成は以下の通りです：

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ定義（バージョンなど）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

各サブパッケージ（data, strategy, execution, monitoring）は拡張ポイントです。必要に応じて以下のようなファイルを追加してください。
- data/
  - loader.py, provider.py, cache.py
- strategy/
  - base.py, examples/*.py
- execution/
  - broker_adapter.py, simulator.py
- monitoring/
  - logger.py, notifier.py, dashboard.py

---

## 開発・貢献

- 新しい機能やバグ修正は Pull Request を通じて歓迎します。PR には変更点の説明と簡単な動作確認手順を添えてください。
- テスト、型チェック（mypy）、静的解析（flake8/black など）のセットアップはプロジェクト方針に合わせて追加してください。

---

## ライセンス・注意事項

- 本 README はプロジェクトの初期ドキュメントです。ライセンスや実運用に関する記載はリポジトリの方針に従って追加してください。  
- 自動売買の実運用はリスクを伴います。実際に運用する場合は十分な検証・モニタリング・法令順守を行ってください。

---

必要であれば、README に以下の追記を行います：
- 具体的なサンプル実装（戦略のテンプレート、バックテストのサンプル）
- 依存関係（requirements.txt）や CI（GitHub Actions）の設定例
- ブローカー（kabuステーション 等）向けアダプタのサンプル

どの内容を優先して追加しますか？