# KabuSys

KabuSys は日本株の自動売買を想定した軽量な Python パッケージの雛形です。  
データ取得、売買戦略、注文実行、監視・ログといった自動売買システムの主要コンポーネントをモジュール化しており、拡張・実装を容易にすることを目的としています。

現在のバージョン: 0.1.0

---

## 機能一覧（想定・テンプレート）

- data: 市場データ（板・約定・OHLC など）の取得・前処理を想定したモジュール
- strategy: 売買アルゴリズム（シグナル生成、ポジション管理）の作成・管理
- execution: ブローカー/証券会社 API を通じた注文送信・キャンセル・約定確認
- monitoring: ログ、アラート、パフォーマンス計測、稼働監視

※ 現状はパッケージ構成のみ提供しており、各モジュールの具体的な実装は含まれていません。テンプレートとして拡張して利用してください。

---

## 要求環境

- Python 3.8 以上を推奨
- OS: 特に制約なし（実際の取引 API を使う場合は API の動作環境に準拠）

外部ライブラリはプロジェクトのニーズに合わせて requirements.txt や pyproject.toml に追加してください（現時点では依存ファイルは含まれていません）。

---

## セットアップ手順

1. リポジトリをクローンする（例）
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成して有効化する（推奨）
   - Linux / macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージを開発モードでインストール
   ```
   pip install --upgrade pip
   pip install -e .
   ```
   - プロジェクトが `src/` レイアウトになっているため、上記コマンドで `kabusys` をローカルソースとして使えます。

4. 依存関係がある場合は、requirements.txt を追加して
   ```
   pip install -r requirements.txt
   ```

5. 実際の取引 API を使う場合は、API キー・認証情報を環境変数または設定ファイルで管理してください（実装に応じて設定方法を追加）。

---

## 使い方（簡単な例）

パッケージが正しくインストールされているか確認する簡単なスクリプト例:

```python
import kabusys

print("KabuSys version:", kabusys.__version__)
print("Available modules:", kabusys.__all__)
```

各モジュールの実装例（骨子）

- data モジュール例
  ```python
  # src/kabusys/data/market.py
  def fetch_ohlcv(symbol, start, end):
      """OHLCV データを取得して pandas.DataFrame を返す（実装例）"""
      pass
  ```

- strategy モジュール例
  ```python
  # src/kabusys/strategy/simple.py
  def generate_signal(df):
      """シグナル（BUY/SELL/HOLD）を生成する"""
      pass
  ```

- execution モジュール例
  ```python
  # src/kabusys/execution/api.py
  def send_order(symbol, side, qty):
      """ブローカー API に注文を送るラッパー（実装）"""
      pass
  ```

- monitoring モジュール例
  ```python
  # src/kabusys/monitoring/logging.py
  def setup_logging():
      """ログ設定を行う"""
      pass
  ```

上記はあくまで雛形です。実際のビジネスロジックや API 呼び出し、エラーハンドリング、リトライ、レート制限対応等は個別に実装してください。

---

## ディレクトリ構成

現在のプロジェクト（主要部分）の構成は以下の通りです:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ情報（バージョン、公開モジュール）
│     ├─ data/
│     │  └─ __init__.py         # データ取得・前処理用モジュール（拡張箇所）
│     ├─ strategy/
│     │  └─ __init__.py         # 売買戦略用モジュール（拡張箇所）
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行用モジュール（拡張箇所）
│     └─ monitoring/
│        └─ __init__.py         # 監視・ロギング用モジュール（拡張箇所）
├─ README.md
└─ setup.py / pyproject.toml    # （任意）パッケージ配布・依存管理用
```

---

## 開発・拡張のヒント

- 各サブパッケージにテストを用意する（例: tests/ ディレクトリ）
- CI を導入して静的解析（flake8、mypy など）やユニットテストを自動化する
- 実トレード接続を行う場合は、必ずサンドボックス環境で十分に検証してから本番環境に移行する
- 機密情報（API キー等）はリポジトリに含めず、環境変数やシークレット管理サービスを利用する

---

## ライセンス・貢献

- ライセンス: プロジェクトに応じて追加してください（例: MIT License）
- 貢献: Issue や Pull Request を歓迎します。変更を行う際は、簡潔な説明とテストを添えてください。

---

この README は現状の雛形パッケージに基づく説明です。各モジュール内に具体的な実装（API ラッパー、戦略アルゴリズム、データ取得関数など）を追加してプロジェクトを完成させてください。必要であれば、個別モジュールの実装テンプレートやサンプルコードの作成も手伝えます。